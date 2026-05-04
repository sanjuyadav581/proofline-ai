"""Approval Packet Assembly — orchestrates the full pipeline with parallelism."""

import uuid
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from backend.models.schemas import (
    ApprovalPacket,
    PublishStatus,
    AuditReport,
    AdaptationResult,
    BrandDNA,
    RiskLedgerEntry,
    ReviewerOpinion,
    ReviewerVerdict,
    Severity,
    Channel,
    Audience,
)
from backend.services.auditor import run_audit
from backend.services.adapter import run_adaptation
# Local import to avoid circular dependency: deterministic_auditor imports schemas,
# approval imports schemas + all services. Keeping this import here breaks the cycle.
from backend.services.deterministic_auditor import run_deterministic_audit
from backend.services.risk_ledger import generate_risk_ledger
from backend.services.reviewers import run_reviewer_panel
from backend.services.brand_dna import score_brand_dna
from backend.database import get_session, ChatSession
from backend.constants import (
    LLM_TIMEOUT_SECONDS,
    VIOLATION_WEIGHT, DNA_WEIGHT,
    CRITICAL_PENALTY, HIGH_PENALTY, MEDIUM_PENALTY, LOW_PENALTY,
)

logger = logging.getLogger(__name__)


def _merge_violations(det_violations, llm_violations):
    """Merge deterministic and LLM violations, deduplicating by rule_id + similar text."""
    # Index deterministic violations by (rule_id, lowercase text) as tuples — safe for text containing colons
    det_index: dict[str, list[str]] = {}  # rule_id → list of original_text (lowered)
    for v in det_violations:
        det_index.setdefault(v.rule_id, []).append(v.original_text.lower().strip())

    merged = list(det_violations)
    for v in llm_violations:
        v_text = v.original_text.lower().strip()
        det_texts = det_index.get(v.rule_id, [])

        # Skip if deterministic already caught exact same rule_id + text
        if v_text in det_texts:
            continue

        # Skip if the LLM text is a substring of a det text or vice versa (same rule)
        is_dup = any(v_text in dt or dt in v_text for dt in det_texts)
        if not is_dup:
            merged.append(v)

    return merged


def run_full_pipeline(
    content: str,
    guideline_id: str,
    channel: str,
    audience: str,
    user_email: str | None = None,
) -> ApprovalPacket:
    """Run the complete Proofline pipeline with parallel LLM calls."""
    run_id = str(uuid.uuid4())
    pipeline_start = datetime.now(timezone.utc)
    timestamp = pipeline_start.isoformat()

    # ── Phase 0: Deterministic audit (instant, no LLM) ──
    logger.info("[%s] Phase 0: Running deterministic audit...", run_id[:8])
    det_violations = run_deterministic_audit(content, channel)

    # ── Phase 1: Audit + Adapt + Brand DNA (before) in parallel ──
    logger.info("[%s] Phase 1: Audit + Adapt + Brand DNA (original) in parallel...", run_id[:8])
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_audit = pool.submit(run_audit, content, guideline_id, channel, audience)
        fut_adapt = pool.submit(run_adaptation, content, guideline_id, channel, audience)
        fut_dna_before = pool.submit(
            score_brand_dna, content, guideline_id, channel, audience,
            AuditReport(violations=[], summary="Scoring original content before audit."),
        )

        llm_audit_report = fut_audit.result(timeout=LLM_TIMEOUT_SECONDS)
        adaptation = fut_adapt.result(timeout=LLM_TIMEOUT_SECONDS)
        brand_dna_before = fut_dna_before.result(timeout=LLM_TIMEOUT_SECONDS)

    # Merge deterministic + LLM violations
    merged = _merge_violations(det_violations, llm_audit_report.violations)
    audit_report = AuditReport(
        violations=merged,
        critical_count=sum(1 for v in merged if v.severity == Severity.CRITICAL),
        high_count=sum(1 for v in merged if v.severity == Severity.HIGH),
        medium_count=sum(1 for v in merged if v.severity == Severity.MEDIUM),
        low_count=sum(1 for v in merged if v.severity == Severity.LOW),
        summary=llm_audit_report.summary,
    )
    logger.info(
        "[%s] Merged audit: %d det + %d LLM → %d total violations",
        run_id[:8], len(det_violations), len(llm_audit_report.violations), len(merged),
    )

    # ── Phase 2: Risk Ledger (fast, no LLM) ──
    logger.info("[%s] Phase 2: Generating risk ledger...", run_id[:8])
    risk_ledger = generate_risk_ledger(audit_report, adaptation)

    # ── Phase 3: Reviewers + Brand DNA (after) in parallel ──
    logger.info("[%s] Phase 3: Reviewers + Brand DNA (adapted) in parallel...", run_id[:8])
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_reviewers = pool.submit(run_reviewer_panel, audit_report, adaptation)
        fut_dna_after = pool.submit(
            score_brand_dna, adaptation.adapted_content, guideline_id,
            channel, audience, audit_report,
        )

        reviewer_panel = fut_reviewers.result(timeout=LLM_TIMEOUT_SECONDS)
        brand_dna = fut_dna_after.result(timeout=LLM_TIMEOUT_SECONDS)

    # ── Phase 4: Assemble approval packet ──
    logger.info("[%s] Phase 4: Assembling approval packet...", run_id[:8])
    publish_status = _determine_publish_status(audit_report, reviewer_panel)
    overall_risk = _compute_risk_score(audit_report, brand_dna)
    unresolved = _find_unresolved(risk_ledger)
    recommendation = _generate_recommendation(publish_status, audit_report, unresolved)

    packet = ApprovalPacket(
        run_id=run_id,
        timestamp=timestamp,
        publish_status=publish_status,
        overall_risk_score=overall_risk,
        audit_report=audit_report,
        brand_dna_before=brand_dna_before,
        brand_dna=brand_dna,
        adaptation=adaptation,
        risk_ledger=risk_ledger,
        reviewer_panel=reviewer_panel,
        unresolved_items=unresolved,
        final_recommendation=recommendation,
    )

    # Persist to Postgres
    pipeline_end = datetime.now(timezone.utc)
    saved = _persist_run(packet, guideline_id, content, channel, audience,
                         start_time=pipeline_start, end_time=pipeline_end, user_email=user_email)
    if not saved:
        packet.persisted = False

    logger.info(
        "[%s] Pipeline complete. Status: %s, Risk: %.0f",
        run_id[:8], publish_status.value, overall_risk,
    )
    return packet


def _determine_publish_status(
    audit: AuditReport,
    reviewers: list[ReviewerOpinion],
) -> PublishStatus:
    """Determine publishability based on audit and reviewer verdicts."""
    if audit.critical_count > 0:
        return PublishStatus.NOT_PUBLISHABLE

    rejected = any(r.verdict == ReviewerVerdict.REJECTED for r in reviewers)
    if rejected:
        return PublishStatus.NOT_PUBLISHABLE

    conditional = any(r.verdict == ReviewerVerdict.CONDITIONAL for r in reviewers)
    if conditional or audit.high_count > 0:
        return PublishStatus.APPROVED_WITH_CONDITIONS

    return PublishStatus.APPROVED


def _compute_risk_score(audit: AuditReport, brand_dna: BrandDNA) -> float:
    """Compute overall risk score (0=safe, 100=high risk).

    Blends weighted violation penalty (60%) with inverse brand DNA score (40%).
    The split reflects that violations are concrete blockers while DNA captures
    softer tone/fit issues that still affect brand risk.
    """
    violation_penalty = (
        audit.critical_count * CRITICAL_PENALTY
        + audit.high_count * HIGH_PENALTY
        + audit.medium_count * MEDIUM_PENALTY
        + audit.low_count * LOW_PENALTY
    )

    # Brand DNA inverse (lower DNA = higher risk)
    dna_scores = [
        brand_dna.brand_fit_score, brand_dna.terminology_compliance,
        brand_dna.claim_risk_score, brand_dna.cta_compliance,
        brand_dna.channel_fit, brand_dna.audience_fit, brand_dna.tone_alignment,
    ]
    avg_dna = sum(dna_scores) / len(dna_scores)
    dna_risk = max(0, 100 - avg_dna)

    # Blend: violations (concrete blockers) + DNA inverse (softer brand risk)
    risk = min(100, violation_penalty * VIOLATION_WEIGHT + dna_risk * DNA_WEIGHT)
    return round(risk, 1)


def _find_unresolved(risk_ledger: list[RiskLedgerEntry]) -> list[str]:
    """Identify items that still need human review."""
    return [
        f"{entry.detected_issue}: {entry.original_text}"
        for entry in risk_ledger
        if entry.final_action == "flagged for review"
    ]


def _generate_recommendation(
    status: PublishStatus,
    audit: AuditReport,
    unresolved: list[str],
) -> str:
    """Generate a plain-English recommendation."""
    if status == PublishStatus.APPROVED:
        return "Content is compliant and ready for publication. No blocking issues found."
    elif status == PublishStatus.APPROVED_WITH_CONDITIONS:
        items = f" {len(unresolved)} items require reviewer attention." if unresolved else ""
        return (
            f"Content is conditionally approved.{items} "
            f"Address {audit.high_count} high-severity issues before publishing."
        )
    else:
        return (
            f"Content is NOT publishable. {audit.critical_count} critical violations "
            f"must be resolved. Review the risk ledger for details."
        )


def _persist_run(
    packet: ApprovalPacket,
    guideline_id: str,
    content: str,
    channel: str,
    audience: str,
    start_time=None,
    end_time=None,
    user_email: str | None = None,
):
    """Save the audit run to Postgres (chat_sessions table). Returns True on success."""
    session = get_session()
    try:
        # chat_sessions table — primary persistence
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()

        cs = ChatSession(
            id=packet.run_id,
            user_email=user_email,
            selected_audience=audience,
            selected_channel=channel,
            source_content=content,
            guideline_id=guideline_id,
            start_time=start_time or datetime.now(timezone.utc),
            end_time=end_time,
            duration_seconds=duration,
            adapted_content=packet.adaptation.adapted_content,
            publish_status=packet.publish_status.value,
            overall_risk_score=packet.overall_risk_score,
            violation_count=len(packet.audit_report.violations),
            critical_count=packet.audit_report.critical_count,
            change_count=len(packet.adaptation.change_log),
            audit_report=packet.audit_report.model_dump(),
            adaptation_result=packet.adaptation.model_dump(),
            risk_ledger=[e.model_dump() for e in packet.risk_ledger],
            reviewer_panel=[r.model_dump() for r in packet.reviewer_panel],
            brand_dna_before=packet.brand_dna_before.model_dump(),
            brand_dna_after=packet.brand_dna.model_dump(),
            approval_packet=packet.model_dump(),
        )
        session.add(cs)

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.warning("Failed to persist audit run: %s", e)
        return False
    finally:
        session.close()
