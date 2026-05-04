"""Guidelines parsing and storage service with chunked ingestion."""

import hashlib
import json
import logging
import re
import uuid
from backend.services.llm import chat_json
from backend.models.schemas import ParsedRule
from backend.database import get_session, Guideline, ParsedRuleRow

logger = logging.getLogger(__name__)

# In-memory cache — process-local, not shared across workers.
# Maps text_hash → (guideline_id, list[ParsedRule])
_cache: dict[str, tuple[str, list[ParsedRule]]] = {}
# Secondary index: guideline_id → list[ParsedRule] (populated alongside _cache)
_id_to_rules: dict[str, list[ParsedRule]] = {}

from backend.constants import CHUNK_WORD_LIMIT, DEDUP_PREFIX_LENGTH


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def _chunk_guidelines(raw_text: str) -> list[str]:
    """Split guidelines into chunks by section boundaries or word count.

    Strategy:
    1. Try splitting on section headers (numbered sections like '1 —', '2 —', '## Section').
    2. If a section is still too long, split by paragraphs within that section.
    3. Guarantee each chunk is ≤ CHUNK_WORD_LIMIT words.
    """
    # Split on section boundaries: lines starting with a number followed by a dash/em-dash
    section_pattern = r'\n(?=\d+\s*[—–-])'
    sections = re.split(section_pattern, raw_text)

    # If no sections detected, split by double newlines
    if len(sections) <= 1:
        sections = raw_text.split("\n\n")

    chunks: list[str] = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        combined = (current_chunk + "\n\n" + section).strip() if current_chunk else section

        if len(combined.split()) <= CHUNK_WORD_LIMIT:
            current_chunk = combined
        else:
            # Flush current chunk
            if current_chunk:
                chunks.append(current_chunk)
            # If this single section exceeds the limit, split by paragraphs
            if len(section.split()) > CHUNK_WORD_LIMIT:
                paragraphs = section.split("\n")
                sub_chunk = ""
                for para in paragraphs:
                    test = (sub_chunk + "\n" + para).strip() if sub_chunk else para
                    if len(test.split()) <= CHUNK_WORD_LIMIT:
                        sub_chunk = test
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = para
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    # If the entire text is short enough, return as single chunk
    if not chunks:
        chunks = [raw_text]

    logger.info("Split guidelines into %d chunks (sizes: %s words)",
                len(chunks), [len(c.split()) for c in chunks])
    return chunks


def _parse_chunk(chunk_text: str, chunk_index: int) -> list[ParsedRule]:
    """Parse a single chunk of guidelines into rules."""
    user_message = (
        f"Parse the following brand guidelines section (chunk {chunk_index + 1}) into structured rules.\n\n"
        "Return a JSON object with a single key 'rules' containing an array of rule objects.\n"
        "Each rule object must have: rule_id, section, rule_type, description, "
        "examples_good (array of strings), examples_bad (array of strings).\n\n"
        "Use rule_id format like RULE-X.Y where X matches the section number if visible.\n"
        "rule_type must be one of: terminology, prohibited_word, claim_standard, cta, tone, channel_format.\n\n"
        f"BRAND GUIDELINES SECTION:\n{chunk_text}"
    )
    result = chat_json("guidelines_parse.txt", user_message, max_completion_tokens=4096)
    rules_data = result.get("rules", [])
    return [ParsedRule(**r) for r in rules_data]


def parse_guidelines(raw_text: str) -> list[ParsedRule]:
    """Parse guidelines — uses chunking for long documents."""
    word_count = len(raw_text.split())

    if word_count <= CHUNK_WORD_LIMIT:
        # Short guidelines: single LLM call (original behavior)
        user_message = (
            "Parse the following brand guidelines into structured rules.\n\n"
            "Return a JSON object with a single key 'rules' containing an array of rule objects.\n"
            "Each rule object must have: rule_id, section, rule_type, description, "
            "examples_good (array of strings), examples_bad (array of strings).\n\n"
            f"BRAND GUIDELINES:\n{raw_text}"
        )
        result = chat_json("guidelines_parse.txt", user_message, max_completion_tokens=16384)
        rules_data = result.get("rules", [])
        rules = [ParsedRule(**r) for r in rules_data]
        logger.info("Parsed %d rules from guidelines (%d words, single pass)", len(rules), word_count)
        return rules

    # Long guidelines: chunk and parse each
    logger.info("Long guidelines detected (%d words). Chunking...", word_count)
    chunks = _chunk_guidelines(raw_text)

    all_rules: list[ParsedRule] = []
    seen_descriptions: set[str] = set()  # deduplicate by description
    skipped_chunks = 0

    for i, chunk in enumerate(chunks):
        logger.info("Parsing chunk %d/%d (%d words)...", i + 1, len(chunks), len(chunk.split()))
        try:
            chunk_rules = _parse_chunk(chunk, i)
            for rule in chunk_rules:
                # Deduplicate: skip if same description already seen
                desc_key = rule.description.lower().strip()[:DEDUP_PREFIX_LENGTH]
                if desc_key not in seen_descriptions:
                    seen_descriptions.add(desc_key)
                    all_rules.append(rule)
        except Exception as e:
            skipped_chunks += 1
            logger.warning("Failed to parse chunk %d/%d: %s", i + 1, len(chunks), e)

    if skipped_chunks:
        logger.warning("%d/%d chunks failed to parse — some rules may be missing", skipped_chunks, len(chunks))

    # Content-addressed rule IDs: stable across re-ingestion
    for rule in all_rules:
        section_num = rule.section.split("—")[0].strip().lstrip("§").strip() if "—" in rule.section else "0"
        try:
            sec = int(section_num)
        except ValueError:
            sec = 0
        desc_hash = hashlib.sha256(rule.description.strip().lower().encode()).hexdigest()[:6]
        rule.rule_id = f"RULE-{sec}.{desc_hash}"

    logger.info("Parsed %d unique rules from %d chunks (%d words total)",
                len(all_rules), len(chunks), word_count)
    return all_rules


def ingest_guidelines(name: str, raw_text: str) -> tuple[str, list[ParsedRule]]:
    """Parse guidelines, store in DB and cache, return (guideline_id, rules)."""
    text_hash = _hash_text(raw_text)

    # 1. Check in-memory cache first (fastest)
    if text_hash in _cache:
        cached_id, cached_rules = _cache[text_hash]
        if cached_rules:
            logger.info(
                "Cache hit (memory) for guideline text (hash=%s). Reusing id=%s with %d rules.",
                text_hash, cached_id[:8], len(cached_rules),
            )
            return cached_id, cached_rules

    # 2. Check Postgres (survives backend restarts) — uses indexed text_hash column
    session = get_session()
    try:
        existing = session.query(Guideline).filter(Guideline.text_hash == text_hash).first()
        if existing and existing.raw_text.strip() == raw_text.strip():
            gid = str(existing.id)
            cached_rules = get_rules(gid)
            if cached_rules:
                _cache[text_hash] = (gid, cached_rules)  # warm the memory cache
                logger.info(
                    "Cache hit (postgres) for guideline text (hash=%s). Reusing id=%s with %d rules.",
                    text_hash, gid[:8], len(cached_rules),
                )
                return gid, cached_rules
    except Exception as e:
        logger.warning("Postgres cache check failed: %s", e)
    finally:
        session.close()

    # 3. No cache — parse with LLM
    rules = parse_guidelines(raw_text)

    # Store in Postgres
    session = get_session()
    try:
        guideline_id = str(uuid.uuid4())
        db_guideline = Guideline(id=guideline_id, name=name, raw_text=raw_text, text_hash=text_hash)
        session.add(db_guideline)

        for rule in rules:
            db_rule = ParsedRuleRow(
                guideline_id=guideline_id,
                rule_id=rule.rule_id,
                section=rule.section,
                rule_type=rule.rule_type,
                description=rule.description,
                examples_good=rule.examples_good,
                examples_bad=rule.examples_bad,
            )
            session.add(db_rule)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    # Cache in memory (single dict keyed by text_hash)
    _cache[text_hash] = (guideline_id, rules)
    _id_to_rules[guideline_id] = rules

    # Store in Qdrant (best-effort — don't block if embeddings fail)
    try:
        from backend.vectorstore.qdrant_client import store_rules
        store_rules(guideline_id, [r.model_dump() for r in rules])
    except Exception as e:
        logger.warning("Qdrant storage failed (non-blocking): %s", e)

    logger.info("Ingested %d rules for guideline '%s' (id=%s)", len(rules), name, guideline_id)
    return guideline_id, rules


def get_rules(guideline_id: str) -> list[ParsedRule]:
    """Retrieve rules for a guideline — from cache, then DB."""
    if guideline_id in _id_to_rules:
        return _id_to_rules[guideline_id]

    session = get_session()
    try:
        rows = (
            session.query(ParsedRuleRow)
            .filter(ParsedRuleRow.guideline_id == guideline_id)
            .all()
        )
        rules = [
            ParsedRule(
                rule_id=r.rule_id,
                section=r.section,
                rule_type=r.rule_type,
                description=r.description,
                examples_good=r.examples_good or [],
                examples_bad=r.examples_bad or [],
            )
            for r in rows
        ]
        _id_to_rules[guideline_id] = rules
        return rules
    finally:
        session.close()


def get_rules_as_text(guideline_id: str) -> str:
    """Get all rules formatted as text for LLM prompts."""
    rules = get_rules(guideline_id)
    lines = []
    for r in rules:
        line = f"[{r.rule_id}] ({r.section}) [{r.rule_type}]: {r.description}"
        if r.examples_bad:
            line += f" | Bad: {', '.join(r.examples_bad)}"
        if r.examples_good:
            line += f" | Good: {', '.join(r.examples_good)}"
        lines.append(line)
    return "\n".join(lines)
