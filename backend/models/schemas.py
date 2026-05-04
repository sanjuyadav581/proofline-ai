from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ── Enums ──

class Channel(str, Enum):
    LINKEDIN = "linkedin"
    EMAIL = "email"
    LANDING_PAGE = "landing_page"
    PRESS_RELEASE = "press_release"
    EVENT_ABSTRACT = "event_abstract"
    BLOG_POST = "blog_post"


class Audience(str, Enum):
    EXECUTIVE = "executive"
    PRACTITIONER = "practitioner"
    TECHNICAL = "technical"
    SALES = "sales"
    CUSTOMER_SUCCESS = "customer_success"
    INVESTOR = "investor"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PublishStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    NOT_PUBLISHABLE = "not_publishable"


class ReviewerVerdict(str, Enum):
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    REJECTED = "rejected"


class ChangeType(str, Enum):
    TERMINOLOGY = "terminology"
    TONE = "tone"
    STRUCTURE = "structure"
    CTA = "cta"
    CLAIM = "claim"
    FORMATTING = "formatting"


class FinalAction(str, Enum):
    AUTO_FIXED = "auto-fixed"
    FLAGGED_FOR_REVIEW = "flagged for review"
    ACCEPTED = "accepted"


class ReviewerStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskCategory(str, Enum):
    BRAND = "brand"
    LEGAL = "legal"
    CHANNEL = "channel"
    AUDIENCE = "audience"


# ── Channel Constraints (derived from brand guidelines §5) ──

CHANNEL_CONSTRAINTS: dict[Channel, dict] = {
    Channel.LINKEDIN: {
        "max_words": 150,
        "paragraph_style": "1-2 sentences per paragraph, white space between",
        "cta_note": "Use only CTAs approved in the brand guidelines.",
    },
    Channel.EMAIL: {
        "max_words": 300,
        "paragraph_style": "2-3 sentences per paragraph",
        "cta_note": "Use only CTAs approved in the brand guidelines.",
    },
    Channel.LANDING_PAGE: {
        "max_words": 200,
        "paragraph_style": "2-3 sentences per paragraph",
        "cta_note": "Use only CTAs approved in the brand guidelines.",
    },
    Channel.PRESS_RELEASE: {
        "max_words": 600,
        "min_words": 400,
        "paragraph_style": "Standard AP style",
        "cta_note": "No CTA in press releases.",
    },
    Channel.EVENT_ABSTRACT: {
        "max_words": 100,
        "min_words": 75,
        "paragraph_style": "Single paragraph",
        "cta_note": "No CTA in event abstracts.",
    },
    Channel.BLOG_POST: {
        "max_words": 800,
        "min_words": 300,
        "paragraph_style": "2-4 sentences per paragraph, use subheadings",
        "cta_note": "Use only CTAs approved in the brand guidelines.",
    },
}

AUDIENCE_TONE: dict[Audience, str] = {
    Audience.EXECUTIVE: (
        "Lead with business outcome, not product feature. "
        "Minimize technical detail. Frame AI as judgment support, not automation."
    ),
    Audience.PRACTITIONER: (
        "Lead with workflow improvement. Can include feature specifics. "
        "Frame AI as time-saving."
    ),
    Audience.TECHNICAL: (
        "Can use technical terminology. Lead with architecture and integration. "
        "Frame AI as data processing layer."
    ),
    Audience.SALES: (
        "Lead with competitive advantage and pipeline impact. "
        "Use revenue-focused language. Frame AI as a deal acceleration tool."
    ),
    Audience.CUSTOMER_SUCCESS: (
        "Lead with retention and customer outcomes. "
        "Emphasize time-to-value and adoption ease. Frame AI as a proactive support tool."
    ),
    Audience.INVESTOR: (
        "Lead with market opportunity and growth metrics. "
        "Use financial language. Frame AI as a scalable competitive moat."
    ),
}


def format_channel_audience_block(channel: str, audience: str) -> str:
    """Format channel constraints and audience tone for LLM prompts (DRY helper).

    Reads from YAML configs so channels/audiences can be edited without code changes.
    Falls back to the hardcoded dicts if YAML loading fails.
    """
    import json
    try:
        from backend.services.prompt_loader import get_channel_constraints, get_audience_tone
        channel_info = get_channel_constraints(channel)
        audience_info = get_audience_tone(audience)
    except Exception:
        channel_info = CHANNEL_CONSTRAINTS.get(Channel(channel), {})
        audience_info = AUDIENCE_TONE.get(Audience(audience), "")
    return (
        f"TARGET CHANNEL: {channel}\n"
        f"CHANNEL CONSTRAINTS: {json.dumps(channel_info)}\n\n"
        f"TARGET AUDIENCE: {audience}\n"
        f"AUDIENCE TONE GUIDANCE: {audience_info}"
    )


# ── Parsed Rule ──

class ParsedRule(BaseModel):
    rule_id: str = Field(description="Unique rule identifier, e.g. RULE-2.1")
    section: str = Field(description="Section heading, e.g. §2 — Approved Product Terminology")
    rule_type: str = Field(description="One of: terminology, prohibited_word, claim_standard, cta, tone, channel_format")
    description: str
    examples_good: list[str] = Field(default_factory=list)
    examples_bad: list[str] = Field(default_factory=list)


# ── Violation ──

class Violation(BaseModel):
    original_text: str = Field(description="Exact text span from content that violates the rule")
    issue_title: str = Field(description="Short title, e.g. 'Prohibited term: leverage'")
    rule_section: str = Field(description="Section reference, e.g. '§3 — Prohibited Words'")
    rule_id: str = Field(description="Rule identifier, e.g. 'RULE-3.1'")
    explanation: str = Field(description="Why this violates the rule")
    severity: Severity
    suggested_fix: str
    blocks_publishing: bool
    source: str = Field(default="llm", description="Origin of this violation: 'deterministic' or 'llm'")


# ── Audit Report ──

class AuditReport(BaseModel):
    violations: list[Violation]
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    summary: str = ""


# ── Brand DNA Fingerprint ──

class BrandDNA(BaseModel):
    brand_fit_score: float = Field(ge=0, le=100)
    terminology_compliance: float = Field(ge=0, le=100)
    claim_risk_score: float = Field(ge=0, le=100, description="100 = safe, 0 = high risk")
    cta_compliance: float = Field(ge=0, le=100)
    channel_fit: float = Field(ge=0, le=100)
    audience_fit: float = Field(ge=0, le=100)
    tone_alignment: float = Field(ge=0, le=100)


# ── Change Log Entry ──

class ChangeLogEntry(BaseModel):
    original_text: str
    changed_text: str
    change_type: str = Field(description="See ChangeType enum: terminology, tone, structure, cta, claim, formatting")
    rule_reference: str
    rationale: str


# ── Adaptation Result ──

class AdaptationResult(BaseModel):
    adapted_content: str
    word_count: int
    channel: str
    audience: str
    change_log: list[ChangeLogEntry]


# ── Risk Ledger Entry ──

class RiskLedgerEntry(BaseModel):
    original_text: str
    detected_issue: str
    rule_violated: str
    risk_category: str = Field(description="See RiskCategory enum: brand, legal, channel, audience")
    severity: Severity
    suggested_replacement: str
    final_action: str = Field(description="See FinalAction enum: auto-fixed, flagged for review, accepted")
    reviewer_status: str = Field(default="pending", description="See ReviewerStatus enum: pending, approved, rejected")


# ── Simulated Reviewer ──

class ReviewerOpinion(BaseModel):
    reviewer_name: str
    verdict: ReviewerVerdict
    top_concerns: list[str]
    reason: str
    confidence_score: float = Field(ge=0, le=1)


# ── Approval Packet ──

class ApprovalPacket(BaseModel):
    run_id: str
    timestamp: str
    publish_status: PublishStatus
    overall_risk_score: float = Field(ge=0, le=100, description="0 = no risk, 100 = maximum risk")
    audit_report: AuditReport
    brand_dna_before: BrandDNA = Field(description="Brand DNA of the ORIGINAL content")
    brand_dna: BrandDNA = Field(description="Brand DNA of the ADAPTED content")
    adaptation: AdaptationResult
    risk_ledger: list[RiskLedgerEntry]
    reviewer_panel: list[ReviewerOpinion]
    unresolved_items: list[str]
    final_recommendation: str
    persisted: bool = Field(default=True, description="False if session save to DB failed")


# ── API Request / Response Models ──

class GuidelineIngestRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=10, max_length=500_000)  # ~100k words max


class GuidelineIngestResponse(BaseModel):
    guideline_id: str
    rule_count: int
    rules: list[ParsedRule]


class AuditRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    guideline_id: str
    channel: str
    audience: str


class AdaptRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    guideline_id: str
    channel: str
    audience: str


class ApproveRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    guideline_id: str
    channel: str
    audience: str
    user_email: str | None = None


class FullPipelineRequest(BaseModel):
    content: str
    guideline_id: str
    channel: str
    audience: str


class FullPipelineResponse(BaseModel):
    approval_packet: ApprovalPacket


# ── Step API Models ──

class BrandDNARequest(BaseModel):
    content: str
    guideline_id: str
    channel: str
    audience: str
    audit_summary: str = ""


class ReviewersRequest(BaseModel):
    audit_report: AuditReport
    adaptation: AdaptationResult


class RiskLedgerRequest(BaseModel):
    audit_report: AuditReport
    adaptation: AdaptationResult


class SaveRunRequest(BaseModel):
    approval_packet: ApprovalPacket
    guideline_id: str
    source_content: str
    channel: str
    audience: str
    user_email: str | None = None


# ── Campaign Consistency Models ──

class ContentAsset(BaseModel):
    label: str = Field(description="Identifier, e.g. 'LinkedIn Post' or 'Email Draft'")
    channel: str
    content: str


class TermInconsistency(BaseModel):
    term_variants: list[str] = Field(description="All variants found, e.g. ['AI-powered', 'AI-assisted']")
    asset_labels: list[str] = Field(description="Which assets use which variant")
    canonical_term: str = Field(description="The brand-approved canonical term")
    rule_reference: str
    severity: Severity


class CTAInconsistency(BaseModel):
    cta_variants: list[str]
    asset_labels: list[str]
    recommended_cta: str
    rule_reference: str


class ToneDrift(BaseModel):
    asset_label: str
    description: str
    direction: str = Field(description="e.g. 'more casual than standard', 'more formal than peers'")
    severity: Severity


class ClaimInconsistency(BaseModel):
    claim: str
    asset_labels: list[str]
    issue: str = Field(description="e.g. 'Claim appears in 3 assets but cited in none'")
    severity: Severity


class ConsistencyReport(BaseModel):
    overall_consistency_score: float = Field(ge=0, le=100)
    term_inconsistencies: list[TermInconsistency]
    cta_inconsistencies: list[CTAInconsistency]
    tone_drifts: list[ToneDrift]
    claim_inconsistencies: list[ClaimInconsistency]
    summary: str
    recommendations: list[str]


class ConsistencyRequest(BaseModel):
    assets: list[ContentAsset]
    guideline_id: str
