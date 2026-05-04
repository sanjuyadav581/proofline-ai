"""Adapt router."""

from fastapi import APIRouter
from backend.models.schemas import AdaptRequest, AdaptationResult
from backend.services.adapter import run_adaptation

router = APIRouter(prefix="/api/v1", tags=["adapt"])


@router.post("/adapt", response_model=AdaptationResult)
def adapt(request: AdaptRequest):
    """Adapt content for a target channel and audience."""
    return run_adaptation(
        content=request.content,
        guideline_id=request.guideline_id,
        channel=request.channel,
        audience=request.audience,
    )
