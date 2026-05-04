"""Config router — serves channel and audience definitions from the database."""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import get_session, ChannelDefinition, AudienceDefinition

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ChannelOut(BaseModel):
    key: str
    label: str
    description: str
    paragraph_style: str
    cta_note: str
    max_words: int | None
    min_words: int | None
    display_order: int


class AudienceOut(BaseModel):
    key: str
    label: str
    description: str
    tone_guidance: str
    ai_framing: str
    display_order: int


@router.get("/channels", response_model=list[ChannelOut])
def list_channels():
    """List all active channel definitions, ordered by display_order."""
    session = get_session()
    try:
        rows = (
            session.query(ChannelDefinition)
            .filter(ChannelDefinition.is_active == True)
            .order_by(ChannelDefinition.display_order)
            .all()
        )
        return [
            ChannelOut(
                key=r.key, label=r.label, description=r.description,
                paragraph_style=r.paragraph_style, cta_note=r.cta_note,
                max_words=r.max_words, min_words=r.min_words,
                display_order=r.display_order,
            )
            for r in rows
        ]
    finally:
        session.close()


@router.get("/audiences", response_model=list[AudienceOut])
def list_audiences():
    """List all active audience definitions, ordered by display_order."""
    session = get_session()
    try:
        rows = (
            session.query(AudienceDefinition)
            .filter(AudienceDefinition.is_active == True)
            .order_by(AudienceDefinition.display_order)
            .all()
        )
        return [
            AudienceOut(
                key=r.key, label=r.label, description=r.description,
                tone_guidance=r.tone_guidance, ai_framing=r.ai_framing,
                display_order=r.display_order,
            )
            for r in rows
        ]
    finally:
        session.close()
