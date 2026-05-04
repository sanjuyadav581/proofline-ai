"""Audit router."""

from fastapi import APIRouter
from backend.models.schemas import AuditRequest, AuditReport
from backend.services.auditor import run_audit

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.post("/audit", response_model=AuditReport)
def audit(request: AuditRequest):
    """Run a brand compliance audit on content."""
    return run_audit(
        content=request.content,
        guideline_id=request.guideline_id,
        channel=request.channel,
        audience=request.audience,
    )
