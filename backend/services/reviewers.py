"""Simulated Reviewer Panel — 4 expert personas evaluate content."""

import logging
from backend.services.llm import chat_json
from backend.models.schemas import (
    ReviewerOpinion,
    ReviewerVerdict,
    AuditReport,
    AdaptationResult,
)

logger = logging.getLogger(__name__)


def run_reviewer_panel(
    audit_report: AuditReport,
    adaptation: AdaptationResult,
) -> list[ReviewerOpinion]:
    """Simulate 4 expert reviewers evaluating the adapted content."""
    violations_text = "\n".join(
        f"- [{v.severity.value.upper()}] {v.issue_title}: {v.original_text} → {v.suggested_fix} (Rule: {v.rule_id})"
        for v in audit_report.violations
    )

    user_message = f"""Evaluate the following adapted content for publication readiness.

ADAPTED CONTENT:
{adaptation.adapted_content}

CHANNEL: {adaptation.channel}
AUDIENCE: {adaptation.audience}
WORD COUNT: {adaptation.word_count}

AUDIT VIOLATIONS FOUND (before adaptation):
{violations_text if violations_text else "No violations found."}

AUDIT SUMMARY: {audit_report.summary}

NUMBER OF CHANGES MADE: {len(adaptation.change_log)}

Return a JSON object with a "reviewers" array containing exactly 4 reviewer objects:
1. Brand Reviewer
2. Legal Reviewer
3. Channel Strategist
4. Revenue Leader

Each reviewer object must have:
- "reviewer_name": string
- "verdict": "approved" | "conditional" | "rejected"
- "top_concerns": array of 0-3 concern strings
- "reason": one-sentence justification
- "confidence_score": float between 0.0 and 1.0"""

    result = chat_json("reviewers_system.txt", user_message, temperature=0.3, max_completion_tokens=2048)

    opinions = []
    for r in result.get("reviewers", []):
        try:
            opinions.append(ReviewerOpinion(
                reviewer_name=r["reviewer_name"],
                verdict=ReviewerVerdict(r["verdict"]),
                top_concerns=r.get("top_concerns", []),
                reason=r.get("reason", ""),
                confidence_score=float(r.get("confidence_score", 0.5)),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed reviewer opinion: %s", e)

    logger.info("Reviewer panel: %d opinions collected", len(opinions))
    return opinions
