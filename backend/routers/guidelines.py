"""Guidelines ingestion and listing router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.schemas import GuidelineIngestRequest, GuidelineIngestResponse
from backend.services.guidelines import ingest_guidelines
from backend.database import get_session, Guideline

router = APIRouter(prefix="/api/v1/guidelines", tags=["guidelines"])


class GuidelineSummary(BaseModel):
    id: str
    name: str
    created_at: str
    text_preview: str


@router.get("/list", response_model=list[GuidelineSummary])
def list_guidelines():
    """List all saved guidelines (name, id, preview)."""
    session = get_session()
    try:
        rows = session.query(Guideline).order_by(Guideline.created_at.desc()).all()
        # Deduplicate by name — keep latest
        seen_names: set[str] = set()
        result = []
        for r in rows:
            if r.name not in seen_names:
                seen_names.add(r.name)
                result.append(GuidelineSummary(
                    id=str(r.id),
                    name=r.name,
                    created_at=str(r.created_at),
                    text_preview=r.raw_text[:150] + "…" if len(r.raw_text) > 150 else r.raw_text,
                ))
        return result
    finally:
        session.close()


@router.get("/{guideline_id}/text")
def get_guideline_text(guideline_id: str):
    """Get full guideline text by ID."""
    session = get_session()
    try:
        row = session.query(Guideline).filter(Guideline.id == guideline_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Guideline not found")
        return {"id": str(row.id), "name": row.name, "text": row.raw_text}
    finally:
        session.close()


@router.get("/{guideline_id}/rules")
def get_rules_list(guideline_id: str):
    """Get all parsed rules for a guideline."""
    from backend.services.guidelines import get_rules
    rules = get_rules(guideline_id)
    return [r.model_dump() for r in rules]


@router.post("/ingest", response_model=GuidelineIngestResponse)
def ingest(request: GuidelineIngestRequest):
    """Parse and store brand guidelines, returning structured rules."""
    guideline_id, rules = ingest_guidelines(request.name, request.text)
    return GuidelineIngestResponse(
        guideline_id=guideline_id,
        rule_count=len(rules),
        rules=rules,
    )
