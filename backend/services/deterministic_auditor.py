"""Deterministic Auditor — fast regex/keyword checks before LLM audit.

Catches hard violations (prohibited words, wrong terminology, invalid CTAs,
channel length limits) without calling the LLM. Results are merged with
LLM audit results in the approval pipeline.
"""

import re
import logging
from backend.models.schemas import Violation, Severity, Channel, CHANNEL_CONSTRAINTS

logger = logging.getLogger(__name__)

# ── Prohibited terms: (pattern, rule_id, rule_section, issue_title, severity, fix, blocks) ──
PROHIBITED_TERMS: list[tuple[str, str, str, str, Severity, str, bool]] = [
    (
        r"\bAI[- ]powered\b",
        "RULE-2.2", "§2 — Approved Product Terminology",
        "Unapproved product descriptor: 'AI-powered'",
        Severity.HIGH, "Use 'AI-assisted' per brand guidelines.", False,
    ),
    (
        r"\bmachine[- ]learning[- ]powered\b",
        "RULE-2.2", "§2 — Approved Product Terminology",
        "Unapproved product descriptor: 'machine learning-powered'",
        Severity.HIGH, "Use 'AI-assisted' per brand guidelines.", False,
    ),
    (
        r"\bleverag(?:e|es|ed|ing)\b",
        "RULE-3.1", "§3 — Prohibited Words and Phrases",
        "Prohibited word: 'leverage'",
        Severity.CRITICAL, "Replace with 'use,' 'apply,' or 'harness.'", True,
    ),
    (
        r"\bseamlessly\b",
        "RULE-3.5", "§3 — Prohibited Words and Phrases",
        "Prohibited word: 'seamlessly'",
        Severity.HIGH, "Replace with 'simply' or remove the qualifier.", False,
    ),
    (
        r"\bindustry[- ]leading\b",
        "RULE-3.4", "§3 — Prohibited Words and Phrases",
        "Unsupported superlative: 'industry-leading'",
        Severity.CRITICAL, "Requires a cited, current third-party source. Remove or add citation.", True,
    ),
    (
        r"\bbest[- ]in[- ]class\b",
        "RULE-3.4", "§3 — Prohibited Words and Phrases",
        "Unsupported superlative: 'best-in-class'",
        Severity.CRITICAL, "Requires a cited, current third-party source. Remove or add citation.", True,
    ),
    (
        r"\brevolutionary\b",
        "RULE-3.3", "§3 — Prohibited Words and Phrases",
        "Prohibited superlative: 'revolutionary'",
        Severity.HIGH, "Avoid superlatives unless citing independent research.", False,
    ),
    (
        r"\bdisrupts?\b",
        "RULE-3.3", "§3 — Prohibited Words and Phrases",
        "Prohibited superlative: 'disrupts'",
        Severity.HIGH, "Avoid superlatives unless citing independent research.", False,
    ),
    (
        r"\bgame[- ]chang(?:ing|er)\b",
        "RULE-3.3", "§3 — Prohibited Words and Phrases",
        "Prohibited superlative: 'game-changing'",
        Severity.HIGH, "Avoid superlatives unless citing independent research.", False,
    ),
    (
        r"\brobust\b",
        "RULE-3.6", "§3 — Prohibited Words and Phrases",
        "Prohibited word: 'robust'",
        Severity.MEDIUM, "Replace with 'reliable,' 'durable,' or be specific.", False,
    ),
    (
        r"\bempowers?\b",
        "RULE-3.8", "§3 — Prohibited Words and Phrases",
        "Prohibited word: 'empower'",
        Severity.MEDIUM, "Replace with 'help,' 'enable,' or 'allow.'", False,
    ),
    (
        r"\bsynerg(?:y|ies|istic)\b",
        "RULE-3.2", "§3 — Prohibited Words and Phrases",
        "Prohibited word: 'synergy/synergistic'",
        Severity.HIGH, "Replace with 'collaboration' or 'combined effect.'", False,
    ),
]

# ── Prohibited CTAs ──
PROHIBITED_CTAS: list[tuple[str, str, str, str]] = [
    (r"\blearn more\b", "RULE-7.2", "§7 — CTA Standards", "Prohibited CTA: 'Learn more' — too vague."),
    (r"\bclick here\b", "RULE-7.2", "§7 — CTA Standards", "Prohibited CTA: 'Click here.'"),
    (r"\bfree trial\b", "RULE-7.2", "§7 — CTA Standards", "Prohibited CTA: 'Free trial' — not aligned with positioning."),
]

DET_TAG = "[deterministic] "


def run_deterministic_audit(content: str, channel: str | None = None) -> list[Violation]:
    """Run fast deterministic checks and return violations."""
    violations: list[Violation] = []

    # ── Prohibited terms ──
    for pattern, rule_id, section, title, severity, fix, blocks in PROHIBITED_TERMS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            violations.append(Violation(
                original_text=match.group(0),
                issue_title=title,
                rule_section=section,
                rule_id=rule_id,
                explanation=f"{DET_TAG}Exact match detected for prohibited/unapproved term.",
                severity=severity,
                suggested_fix=fix,
                blocks_publishing=blocks,
                source="deterministic",
            ))

    # ── Prohibited CTAs ──
    for pattern, rule_id, section, title in PROHIBITED_CTAS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            violations.append(Violation(
                original_text=match.group(0),
                issue_title=title,
                rule_section=section,
                rule_id=rule_id,
                explanation=f"{DET_TAG}Prohibited CTA detected.",
                severity=Severity.HIGH,
                suggested_fix="Replace with an approved CTA from the brand guidelines (e.g. 'See a demo,' 'Talk to sales').",
                blocks_publishing=False,
                source="deterministic",
            ))

    # ── Channel length checks ──
    if channel:
        word_count = len(content.split())
        # Look up constraints — try str key first (for DB-driven channels), then enum key
        constraints = CHANNEL_CONSTRAINTS.get(channel, {})
        if not constraints:
            try:
                constraints = CHANNEL_CONSTRAINTS.get(Channel(channel), {})
            except ValueError:
                pass
        # Also check DB-driven constraints via prompt_loader
        if not constraints:
            try:
                from backend.services.prompt_loader import get_channel_constraints
                constraints = get_channel_constraints(channel)
            except Exception:
                pass
        max_words = constraints.get("max_words")
        min_words = constraints.get("min_words")

        if max_words and word_count > max_words:
            violations.append(Violation(
                original_text=f"Content is {word_count} words",
                issue_title=f"Exceeds {channel} word limit ({max_words} max)",
                rule_section="§5 — Channel-Specific Length and Format",
                rule_id="RULE-5.1",
                explanation=f"{DET_TAG}Content is {word_count} words, exceeding the {max_words}-word limit for {channel}.",
                severity=Severity.HIGH,
                suggested_fix=f"Reduce content to {max_words} words or fewer.",
                blocks_publishing=False,
                source="deterministic",
            ))

        if min_words and word_count < min_words:
            violations.append(Violation(
                original_text=f"Content is {word_count} words",
                issue_title=f"Below {channel} minimum ({min_words} min)",
                rule_section="§5 — Channel-Specific Length and Format",
                rule_id="RULE-5.1",
                explanation=f"{DET_TAG}Content is {word_count} words, below the {min_words}-word minimum for {channel}.",
                severity=Severity.MEDIUM,
                suggested_fix=f"Expand content to at least {min_words} words.",
                blocks_publishing=False,
                source="deterministic",
            ))

    # Deduplicate by (rule_id, original_text) — keep first occurrence
    seen: set[tuple[str, str]] = set()
    unique: list[Violation] = []
    for v in violations:
        key = (v.rule_id, v.original_text.lower())
        if key not in seen:
            seen.add(key)
            unique.append(v)

    logger.info("Deterministic audit: %d violations found", len(unique))
    return unique
