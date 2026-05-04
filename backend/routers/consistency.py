"""Consistency router — cross-asset campaign consistency check."""

from fastapi import APIRouter
from backend.models.schemas import ConsistencyRequest, ConsistencyReport
from backend.services.consistency import run_consistency_check

router = APIRouter(prefix="/api/v1", tags=["consistency"])


@router.post("/consistency", response_model=ConsistencyReport)
def consistency(request: ConsistencyRequest):
    """Check multiple content assets for cross-channel consistency."""
    return run_consistency_check(
        assets=request.assets,
        guideline_id=request.guideline_id,
    )
