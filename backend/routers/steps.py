"""Step-by-step pipeline endpoints for real progress tracking."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.models.schemas import (
    BrandDNARequest, BrandDNA, AuditReport,
    ReviewersRequest, ReviewerOpinion,
    RiskLedgerRequest, RiskLedgerEntry,
)
from backend.services.brand_dna import score_brand_dna
from backend.services.reviewers import run_reviewer_panel
from backend.services.risk_ledger import generate_risk_ledger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/steps", tags=["steps"])


class SaveSessionRequest(BaseModel):
    run_id: str
    guideline_id: str
    source_content: str
    selected_channel: str
    selected_audience: str
    adapted_content: str = ""
    publish_status: str = ""
    overall_risk_score: float = 0
    violation_count: int = 0
    critical_count: int = 0
    change_count: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0
    audit_report: dict = Field(default_factory=dict)
    adaptation_result: dict = Field(default_factory=dict)
    risk_ledger: list = Field(default_factory=list)
    reviewer_panel: list = Field(default_factory=list)
    brand_dna_before: dict = Field(default_factory=dict)
    brand_dna_after: dict = Field(default_factory=dict)
    approval_packet: dict = Field(default_factory=dict)
    user_email: str | None = None


@router.post("/save-session")
def save_session(req: SaveSessionRequest):
    """Persist a completed pipeline run to chat_sessions."""
    from backend.database import get_session, ChatSession

    session = get_session()
    try:
        # Parse times
        try:
            st_time = datetime.fromisoformat(req.start_time) if req.start_time else datetime.now(timezone.utc)
            en_time = datetime.fromisoformat(req.end_time) if req.end_time else datetime.now(timezone.utc)
        except Exception:
            st_time = datetime.now(timezone.utc)
            en_time = datetime.now(timezone.utc)

        # Save to chat_sessions
        cs = ChatSession(
            id=req.run_id,
            user_email=req.user_email,
            selected_audience=req.selected_audience,
            selected_channel=req.selected_channel,
            source_content=req.source_content,
            guideline_id=req.guideline_id,
            start_time=st_time,
            end_time=en_time,
            duration_seconds=req.duration_seconds,
            adapted_content=req.adapted_content,
            publish_status=req.publish_status,
            overall_risk_score=req.overall_risk_score,
            violation_count=req.violation_count,
            critical_count=req.critical_count,
            change_count=req.change_count,
            audit_report=req.audit_report,
            adaptation_result=req.adaptation_result,
            risk_ledger=req.risk_ledger,
            reviewer_panel=req.reviewer_panel,
            brand_dna_before=req.brand_dna_before,
            brand_dna_after=req.brand_dna_after,
            approval_packet=req.approval_packet,
        )
        session.add(cs)
        session.commit()
        logger.info("Saved session %s to chat_sessions", req.run_id[:8])
        return {"status": "saved", "run_id": req.run_id}
    except Exception as e:
        session.rollback()
        logger.warning("Failed to save session: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save session: {e}")
    finally:
        session.close()


@router.post("/brand-dna", response_model=BrandDNA)
def step_brand_dna(request: BrandDNARequest):
    """Score content on 7 brand dimensions."""
    dummy_audit = AuditReport(violations=[], summary=request.audit_summary)
    return score_brand_dna(
        content=request.content,
        guideline_id=request.guideline_id,
        channel=request.channel,
        audience=request.audience,
        audit_report=dummy_audit,
    )


@router.post("/reviewers", response_model=list[ReviewerOpinion])
def step_reviewers(request: ReviewersRequest):
    """Simulate 4 expert reviewers."""
    return run_reviewer_panel(request.audit_report, request.adaptation)


@router.post("/risk-ledger", response_model=list[RiskLedgerEntry])
def step_risk_ledger(request: RiskLedgerRequest):
    """Generate risk ledger from audit + adaptation."""
    return generate_risk_ledger(request.audit_report, request.adaptation)
