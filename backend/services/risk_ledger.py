"""Risk Ledger — generates audit trail from violations and adaptation."""

import logging
from backend.models.schemas import (
    RiskLedgerEntry,
    AuditReport,
    AdaptationResult,
    Severity,
)

logger = logging.getLogger(__name__)


def generate_risk_ledger(
    audit_report: AuditReport,
    adaptation: AdaptationResult,
) -> list[RiskLedgerEntry]:
    """Build a risk ledger combining audit violations with adaptation actions."""
    ledger: list[RiskLedgerEntry] = []

    # Map adapted changes by original text for cross-referencing
    changes_by_original: dict[str, str] = {}
    for change in adaptation.change_log:
        changes_by_original[change.original_text.lower().strip()] = change.changed_text

    for violation in audit_report.violations:
        original_lower = violation.original_text.lower().strip()

        # Check if this violation was addressed in adaptation
        was_fixed = any(
            original_lower in key or key in original_lower
            for key in changes_by_original
        )

        if was_fixed:
            final_action = "auto-fixed"
            replacement = next(
                (v for k, v in changes_by_original.items()
                 if original_lower in k or k in original_lower),
                violation.suggested_fix,
            )
        elif violation.blocks_publishing:
            final_action = "flagged for review"
            replacement = violation.suggested_fix
        else:
            final_action = "flagged for review"
            replacement = violation.suggested_fix

        # Determine risk category from rule type
        risk_category = _classify_risk(violation.rule_section, violation.issue_title)

        ledger.append(RiskLedgerEntry(
            original_text=violation.original_text,
            detected_issue=violation.issue_title,
            rule_violated=f"{violation.rule_id} ({violation.rule_section})",
            risk_category=risk_category,
            severity=violation.severity,
            suggested_replacement=replacement,
            final_action=final_action,
            reviewer_status="pending",
        ))

    logger.info("Risk ledger generated with %d entries", len(ledger))
    return ledger


def _classify_risk(rule_section: str, issue_title: str) -> str:
    """Classify a violation into a risk category."""
    lower_section = rule_section.lower()
    lower_title = issue_title.lower()

    if any(kw in lower_section or kw in lower_title for kw in ["claim", "legal", "citation"]):
        return "legal"
    if any(kw in lower_section or kw in lower_title for kw in ["channel", "format", "length"]):
        return "channel"
    if any(kw in lower_section or kw in lower_title for kw in ["audience", "tone"]):
        return "audience"
    return "brand"
