"""Brand DNA Fingerprint — scores content on 7 brand alignment dimensions."""

import logging
from backend.services.llm import chat_json, render_template
from backend.services.guidelines import get_rules_as_text
from backend.services.prompt_loader import get_channel_constraints, get_audience_tone
from backend.models.schemas import (
    BrandDNA,
    AuditReport,
    Channel,
    Audience,
)

logger = logging.getLogger(__name__)


def score_brand_dna(
    content: str,
    guideline_id: str,
    channel: str,
    audience: str,
    audit_report: AuditReport,
) -> BrandDNA:
    """Score content on 7 brand alignment dimensions."""
    rules_text = get_rules_as_text(guideline_id)

    violations_summary = f"{audit_report.critical_count} critical, {audit_report.high_count} high, {audit_report.medium_count} medium, {audit_report.low_count} low violations"

    import json
    user_message = render_template(
        "brand_dna_user.j2",
        channel=channel,
        channel_constraints=json.dumps(get_channel_constraints(channel)),
        audience=audience,
        audience_tone=get_audience_tone(audience),
        rules_text=rules_text,
        content=content,
        violations_summary=violations_summary,
    )

    result = chat_json("brand_dna_system.txt", user_message, max_completion_tokens=1024)

    brand_dna = BrandDNA(
        brand_fit_score=float(result.get("brand_fit_score", 50)),
        terminology_compliance=float(result.get("terminology_compliance", 50)),
        claim_risk_score=float(result.get("claim_risk_score", 50)),
        cta_compliance=float(result.get("cta_compliance", 50)),
        channel_fit=float(result.get("channel_fit", 50)),
        audience_fit=float(result.get("audience_fit", 50)),
        tone_alignment=float(result.get("tone_alignment", 50)),
    )

    logger.info("Brand DNA scored: avg=%.1f", sum([
        brand_dna.brand_fit_score, brand_dna.terminology_compliance,
        brand_dna.claim_risk_score, brand_dna.cta_compliance,
        brand_dna.channel_fit, brand_dna.audience_fit, brand_dna.tone_alignment,
    ]) / 7)
    return brand_dna
