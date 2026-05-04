"""Brand Compliance Auditor — detects violations with rule citations.

Uses Qdrant semantic retrieval to find the most relevant rules for the content,
then sends only those rules to the LLM for focused audit.
Falls back to all rules if Qdrant retrieval fails.
"""

import logging
from backend.services.llm import chat_json, render_template
from backend.services.guidelines import get_rules_as_text, get_rules
from backend.services.prompt_loader import get_channel_constraints, get_audience_tone
from backend.models.schemas import (
    AuditReport,
    Violation,
    Severity,
    Channel,
    Audience,
)

logger = logging.getLogger(__name__)

from backend.constants import TOP_K_RULES, MAX_TOTAL_RULES


def _retrieve_relevant_rules(content: str, guideline_id: str) -> str:
    """Use Qdrant to find rules most relevant to the content.

    Splits content into paragraphs, retrieves top-K rules per paragraph,
    deduplicates, and formats as text for the LLM prompt.
    Falls back to all rules if Qdrant is unavailable.
    """
    # Local import to avoid circular dependency with vectorstore module
    try:
        from backend.vectorstore.qdrant_client import search_relevant_rules
    except Exception:
        logger.warning("Qdrant import failed, falling back to all rules")
        return get_rules_as_text(guideline_id)

    # Split content into paragraphs for more focused retrieval
    paragraphs = [p.strip() for p in content.split("\n") if p.strip() and len(p.strip().split()) > 3]
    if not paragraphs:
        paragraphs = [content]

    # Also search with the full content to catch holistic rules (tone, voice)
    all_payloads: dict[str, dict] = {}  # rule_id → payload (dedup)

    try:
        # Retrieve rules for each paragraph
        for para in paragraphs:
            results = search_relevant_rules(para, guideline_id, top_k=TOP_K_RULES)
            for r in results:
                rid = r.get("rule_id", "")
                if rid and rid not in all_payloads:
                    all_payloads[rid] = r

        # Also do a full-content search for holistic rules
        full_results = search_relevant_rules(content[:1000], guideline_id, top_k=TOP_K_RULES)
        for r in full_results:
            rid = r.get("rule_id", "")
            if rid and rid not in all_payloads:
                all_payloads[rid] = r

    except Exception as e:
        logger.warning("Qdrant retrieval failed (%s), falling back to all rules", e)
        return get_rules_as_text(guideline_id)

    if not all_payloads:
        logger.warning("Qdrant returned no rules, falling back to all rules")
        return get_rules_as_text(guideline_id)

    # Cap total rules to avoid blowing up the audit prompt
    if len(all_payloads) > MAX_TOTAL_RULES:
        logger.info("Capping retrieved rules from %d to %d", len(all_payloads), MAX_TOTAL_RULES)
        all_payloads = dict(list(all_payloads.items())[:MAX_TOTAL_RULES])

    # Format retrieved rules as text
    lines = []
    for r in all_payloads.values():
        line = f"[{r['rule_id']}] ({r['section']}) [{r['rule_type']}]: {r['description']}"
        if r.get("examples_bad"):
            line += f" | Bad: {', '.join(r['examples_bad'])}"
        if r.get("examples_good"):
            line += f" | Good: {', '.join(r['examples_good'])}"
        lines.append(line)

    logger.info(
        "Qdrant retrieval: %d unique rules from %d paragraphs (out of %d total rules)",
        len(all_payloads), len(paragraphs),
        len(get_rules(guideline_id)),
    )
    return "\n".join(lines)


def run_audit(
    content: str,
    guideline_id: str,
    channel: str,
    audience: str,
) -> AuditReport:
    """Audit content against brand guidelines and return a violation report."""
    # Use semantic retrieval for focused, relevant rules
    rules_text = _retrieve_relevant_rules(content, guideline_id)

    import json
    user_message = render_template(
        "audit_user.j2",
        channel=channel,
        channel_constraints=json.dumps(get_channel_constraints(channel)),
        audience=audience,
        audience_tone=get_audience_tone(audience),
        rules_text=rules_text,
        content=content,
    )

    result = chat_json("audit_system.txt", user_message, max_completion_tokens=4096)

    # Fail closed: if LLM response was degraded, surface it rather than returning "clean"
    degraded = result.get("_degraded", False)

    violations = []
    for v in result.get("violations", []):
        try:
            violations.append(Violation(
                original_text=v["original_text"],
                issue_title=v["issue_title"],
                rule_section=v["rule_section"],
                rule_id=v["rule_id"],
                explanation=v["explanation"],
                severity=Severity(v["severity"]),
                suggested_fix=v["suggested_fix"],
                blocks_publishing=v.get("blocks_publishing", False),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed violation: %s", e)

    summary = result.get("summary", "")
    if degraded:
        summary = "⚠ DEGRADED: LLM audit response was malformed. Results may be incomplete. " + summary

    report = AuditReport(
        violations=violations,
        critical_count=sum(1 for v in violations if v.severity == Severity.CRITICAL),
        high_count=sum(1 for v in violations if v.severity == Severity.HIGH),
        medium_count=sum(1 for v in violations if v.severity == Severity.MEDIUM),
        low_count=sum(1 for v in violations if v.severity == Severity.LOW),
        summary=summary,
    )

    logger.info(
        "Audit complete: %d violations (%d critical, %d high)",
        len(violations), report.critical_count, report.high_count,
    )
    return report
