"""Campaign Consistency Checker — detects inconsistencies across multiple content assets."""

import json
import logging
from backend.services.llm import chat_json
from backend.services.guidelines import get_rules_as_text
from backend.models.schemas import (
    ContentAsset,
    ConsistencyReport,
    TermInconsistency,
    CTAInconsistency,
    ToneDrift,
    ClaimInconsistency,
    Severity,
)

logger = logging.getLogger(__name__)


def run_consistency_check(
    assets: list[ContentAsset],
    guideline_id: str,
) -> ConsistencyReport:
    """Compare multiple content assets for cross-channel consistency."""
    rules_text = get_rules_as_text(guideline_id)

    # Format assets for the prompt
    assets_text = ""
    for i, asset in enumerate(assets, 1):
        assets_text += f"\n--- ASSET {i}: {asset.label} (channel: {asset.channel}) ---\n"
        assets_text += asset.content + "\n"

    user_message = f"""Analyze the following {len(assets)} content assets from the same brand campaign for consistency.

BRAND RULES:
{rules_text}

CONTENT ASSETS:
{assets_text}

Return a JSON object with:
- "overall_consistency_score": float 0-100
- "term_inconsistencies": array of objects, each with:
  - "term_variants": array of variant strings found
  - "asset_labels": array of which asset uses which variant
  - "canonical_term": the brand-approved term
  - "rule_reference": rule_id
  - "severity": "critical" | "high" | "medium" | "low"
- "cta_inconsistencies": array of objects, each with:
  - "cta_variants": array of CTA strings found
  - "asset_labels": array of which asset uses which CTA
  - "recommended_cta": approved CTA for each channel
  - "rule_reference": rule_id
- "tone_drifts": array of objects, each with:
  - "asset_label": which asset drifts
  - "description": what the drift is
  - "direction": e.g. "more casual than standard"
  - "severity": "critical" | "high" | "medium" | "low"
- "claim_inconsistencies": array of objects, each with:
  - "claim": the claim text
  - "asset_labels": which assets contain it
  - "issue": description of the inconsistency
  - "severity": "critical" | "high" | "medium" | "low"
- "summary": one paragraph summary
- "recommendations": array of 3-5 actionable strings

Only flag real inconsistencies. If assets are consistent, return empty arrays and a high score."""

    result = chat_json("consistency_system.txt", user_message, max_completion_tokens=4096)

    # Parse term inconsistencies
    term_issues = []
    for t in result.get("term_inconsistencies", []):
        try:
            term_issues.append(TermInconsistency(
                term_variants=t["term_variants"],
                asset_labels=t["asset_labels"],
                canonical_term=t["canonical_term"],
                rule_reference=t.get("rule_reference", ""),
                severity=Severity(t.get("severity", "medium")),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed term inconsistency: %s", e)

    # Parse CTA inconsistencies
    cta_issues = []
    for c in result.get("cta_inconsistencies", []):
        try:
            cta_issues.append(CTAInconsistency(
                cta_variants=c["cta_variants"],
                asset_labels=c["asset_labels"],
                recommended_cta=c.get("recommended_cta", ""),
                rule_reference=c.get("rule_reference", ""),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed CTA inconsistency: %s", e)

    # Parse tone drifts
    tone_issues = []
    for td in result.get("tone_drifts", []):
        try:
            tone_issues.append(ToneDrift(
                asset_label=td["asset_label"],
                description=td["description"],
                direction=td.get("direction", ""),
                severity=Severity(td.get("severity", "medium")),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed tone drift: %s", e)

    # Parse claim inconsistencies
    claim_issues = []
    for cl in result.get("claim_inconsistencies", []):
        try:
            claim_issues.append(ClaimInconsistency(
                claim=cl["claim"],
                asset_labels=cl["asset_labels"],
                issue=cl["issue"],
                severity=Severity(cl.get("severity", "medium")),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed claim inconsistency: %s", e)

    report = ConsistencyReport(
        overall_consistency_score=float(result.get("overall_consistency_score", 50)),
        term_inconsistencies=term_issues,
        cta_inconsistencies=cta_issues,
        tone_drifts=tone_issues,
        claim_inconsistencies=claim_issues,
        summary=result.get("summary", ""),
        recommendations=result.get("recommendations", []),
    )

    total_issues = len(term_issues) + len(cta_issues) + len(tone_issues) + len(claim_issues)
    logger.info(
        "Consistency check complete: score=%.0f, %d issues across %d assets",
        report.overall_consistency_score, total_issues, len(assets),
    )
    return report
