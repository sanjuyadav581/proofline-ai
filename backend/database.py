"""Postgres database connection and table definitions."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    Boolean,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import get_settings

Base = declarative_base()


# ── Dynamic Channel & Audience Definitions ──

class ChannelDefinition(Base):
    """Channels are defined here. Add a row → auto-reflects in frontend + backend."""
    __tablename__ = "channel_definitions"
    key = Column(String(50), primary_key=True)                # e.g. "linkedin"
    label = Column(String(100), nullable=False)               # e.g. "LinkedIn"
    description = Column(String(255), nullable=False, default="")
    paragraph_style = Column(String(255), nullable=False, default="")
    cta_note = Column(String(255), nullable=False, default="")
    max_words = Column(Integer, nullable=True)
    min_words = Column(Integer, nullable=True)
    display_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)


class AudienceDefinition(Base):
    """Audiences are defined here. Add a row → auto-reflects in frontend + backend."""
    __tablename__ = "audience_definitions"
    key = Column(String(50), primary_key=True)                # e.g. "executive"
    label = Column(String(100), nullable=False)               # e.g. "Executive (VP+)"
    description = Column(String(255), nullable=False, default="")
    tone_guidance = Column(Text, nullable=False, default="")
    ai_framing = Column(String(255), nullable=False, default="")
    display_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)


class Guideline(Base):
    __tablename__ = "guidelines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    text_hash = Column(String(16), index=True, nullable=True)  # SHA-256 prefix for fast cache lookup
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ParsedRuleRow(Base):
    __tablename__ = "parsed_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guideline_id = Column(UUID(as_uuid=True), ForeignKey("guidelines.id", ondelete="CASCADE"), index=True)
    rule_id = Column(String(50), nullable=False)
    section = Column(String(255))
    rule_type = Column(String(50))
    description = Column(Text, nullable=False)
    examples_good = Column(ARRAY(Text), default=list)
    examples_bad = Column(ARRAY(Text), default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    """Primary session table — tracks each Proofline run end-to-end."""
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_email = Column(String(255), nullable=True)          # extracted from browser if available
    selected_audience = Column(String(50), nullable=False)
    selected_channel = Column(String(50), nullable=False)
    source_content = Column(Text, nullable=False)            # original content pasted by user
    guideline_id = Column(UUID(as_uuid=True), ForeignKey("guidelines.id", ondelete="CASCADE"))
    start_time = Column(DateTime(timezone=True), nullable=False)  # pipeline start
    end_time = Column(DateTime(timezone=True), nullable=True)     # pipeline end
    duration_seconds = Column(Float, nullable=True)          # end - start in seconds
    adapted_content = Column(Text, nullable=True)            # rewritten content suggested by the app
    publish_status = Column(String(50), nullable=True)
    overall_risk_score = Column(Float, nullable=True)
    violation_count = Column(Integer, nullable=True)
    critical_count = Column(Integer, nullable=True)
    change_count = Column(Integer, nullable=True)
    audit_report = Column(JSONB, nullable=True)
    adaptation_result = Column(JSONB, nullable=True)
    risk_ledger = Column(JSONB, nullable=True)
    reviewer_panel = Column(JSONB, nullable=True)
    brand_dna_before = Column(JSONB, nullable=True)
    brand_dna_after = Column(JSONB, nullable=True)
    approval_packet = Column(JSONB, nullable=True)           # full result blob

    __table_args__ = (
        Index("ix_chat_sessions_start_time", "start_time"),
        Index("ix_chat_sessions_publish_status", "publish_status"),
        Index("ix_chat_sessions_channel", "selected_channel"),
        Index("ix_chat_sessions_audience", "selected_audience"),
    )


# ── Engine & Session ──

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Create all tables if they don't exist, then seed channels/audiences from YAML."""
    import logging
    engine = get_engine()
    Base.metadata.create_all(engine)
    _seed_definitions(logging.getLogger(__name__))


def _seed_definitions(logger):
    """Seed channel_definitions and audience_definitions from YAML if table is empty."""
    from backend.services.prompt_loader import load_channels, load_audiences
    session = get_session()
    try:
        # Seed channels
        if session.query(ChannelDefinition).count() == 0:
            channels = load_channels()
            for order, (key, cfg) in enumerate(channels.items(), 1):
                session.add(ChannelDefinition(
                    key=key,
                    label=cfg.get("label", key),
                    description=cfg.get("paragraph_style", ""),
                    paragraph_style=cfg.get("paragraph_style", ""),
                    cta_note=cfg.get("cta_note", ""),
                    max_words=cfg.get("max_words"),
                    min_words=cfg.get("min_words"),
                    display_order=order,
                ))
            session.commit()
            logger.info("Seeded %d channel definitions from YAML", len(channels))

        # Seed audiences
        if session.query(AudienceDefinition).count() == 0:
            audiences = load_audiences()
            for order, (key, cfg) in enumerate(audiences.items(), 1):
                tone = cfg.get("tone_guidance", "")
                # Extract AI framing hint (last sentence typically)
                parts = [s.strip() for s in tone.split(".") if s.strip()]
                ai_hint = parts[-1] + "." if parts else ""
                desc = parts[0] + "." if parts else ""
                session.add(AudienceDefinition(
                    key=key,
                    label=cfg.get("label", key),
                    description=desc,
                    tone_guidance=tone.strip(),
                    ai_framing=ai_hint,
                    display_order=order,
                ))
            session.commit()
            logger.info("Seeded %d audience definitions from YAML", len(audiences))
    except Exception as e:
        session.rollback()
        logger.warning("Failed to seed definitions: %s", e)
    finally:
        session.close()
