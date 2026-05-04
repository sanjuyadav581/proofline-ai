"""Approve router — runs the full Proofline pipeline."""

from fastapi import APIRouter
from backend.models.schemas import ApproveRequest, ApprovalPacket
from backend.services.approval import run_full_pipeline

router = APIRouter(prefix="/api/v1", tags=["approve"])


@router.post("/approve", response_model=ApprovalPacket)
def approve(request: ApproveRequest):
    """Run the full Proofline pipeline: audit → adapt → risk ledger → review → approve."""
    return run_full_pipeline(
        content=request.content,
        guideline_id=request.guideline_id,
        channel=request.channel,
        audience=request.audience,
        user_email=request.user_email,
    )
