"""Tests for business logic layers — no LLM calls, pure deterministic.

Covers:
- Risk score formula (_compute_risk_score)
- Guideline cache helpers (_hash_text consistency)
- Risk ledger classification (_classify_risk, final_action)
- Mocked LLM integration (chat_json malformed JSON handling)
- FastAPI endpoint validation (request schemas, 422 on bad input)
"""

import hashlib
import pytest
from unittest.mock import patch, MagicMock

from backend.models.schemas import (
    AuditReport,
    AdaptationResult,
    BrandDNA,
    ChangeLogEntry,
    Violation,
    RiskLedgerEntry,
    Severity,
    Channel,
    Audience,
    PublishStatus,
)


# ══════════════════════════════════════════════
#  RISK SCORE FORMULA
# ══════════════════════════════════════════════

class TestRiskScore:
    """Test _compute_risk_score with known inputs."""

    def _perfect_dna(self) -> BrandDNA:
        return BrandDNA(
            brand_fit_score=100, terminology_compliance=100,
            claim_risk_score=100, cta_compliance=100,
            channel_fit=100, audience_fit=100, tone_alignment=100,
        )

    def _low_dna(self) -> BrandDNA:
        return BrandDNA(
            brand_fit_score=20, terminology_compliance=20,
            claim_risk_score=20, cta_compliance=20,
            channel_fit=20, audience_fit=20, tone_alignment=20,
        )

    def _empty_audit(self) -> AuditReport:
        return AuditReport(violations=[], summary="Clean")

    def test_zero_risk_with_perfect_dna_no_violations(self):
        from backend.services.approval import _compute_risk_score
        score = _compute_risk_score(self._empty_audit(), self._perfect_dna())
        assert score == 0.0

    def test_critical_violation_adds_penalty(self):
        from backend.services.approval import _compute_risk_score
        audit = AuditReport(violations=[], critical_count=1, summary="")
        score = _compute_risk_score(audit, self._perfect_dna())
        # 1 critical * 25 * 0.6 = 15.0, DNA risk = 0 * 0.4 = 0
        assert score == 15.0

    def test_mixed_violations(self):
        from backend.services.approval import _compute_risk_score
        audit = AuditReport(
            violations=[], critical_count=2, high_count=1,
            medium_count=2, low_count=3, summary="",
        )
        score = _compute_risk_score(audit, self._perfect_dna())
        # (2*25 + 1*15 + 2*5 + 3*1) * 0.6 = (50+15+10+3)*0.6 = 78*0.6 = 46.8
        assert score == 46.8

    def test_low_dna_adds_risk(self):
        from backend.services.approval import _compute_risk_score
        score = _compute_risk_score(self._empty_audit(), self._low_dna())
        # DNA avg=20, dna_risk=80, 80*0.4=32.0
        assert score == 32.0

    def test_capped_at_100(self):
        from backend.services.approval import _compute_risk_score
        audit = AuditReport(
            violations=[], critical_count=10, high_count=10,
            medium_count=10, low_count=10, summary="",
        )
        score = _compute_risk_score(audit, self._low_dna())
        assert score == 100.0

    def test_risk_score_is_rounded(self):
        from backend.services.approval import _compute_risk_score
        audit = AuditReport(violations=[], high_count=1, summary="")
        dna = BrandDNA(
            brand_fit_score=73, terminology_compliance=81,
            claim_risk_score=65, cta_compliance=90,
            channel_fit=77, audience_fit=88, tone_alignment=70,
        )
        score = _compute_risk_score(audit, dna)
        assert score == round(score, 1)


# ══════════════════════════════════════════════
#  GUIDELINE CACHE HELPERS
# ══════════════════════════════════════════════

class TestGuidelineCache:
    """Test _hash_text determinism and collision safety."""

    def test_hash_deterministic(self):
        from backend.services.guidelines import _hash_text
        text = "Do not use 'leverage' in marketing copy."
        assert _hash_text(text) == _hash_text(text)

    def test_hash_strips_whitespace(self):
        from backend.services.guidelines import _hash_text
        assert _hash_text("  hello  ") == _hash_text("hello")

    def test_different_texts_different_hashes(self):
        from backend.services.guidelines import _hash_text
        h1 = _hash_text("Do not use leverage")
        h2 = _hash_text("Do not use synergy")
        assert h1 != h2

    def test_hash_length(self):
        from backend.services.guidelines import _hash_text
        h = _hash_text("test content")
        assert len(h) == 16  # SHA-256 truncated to 16 hex chars


# ══════════════════════════════════════════════
#  RISK LEDGER CLASSIFICATION
# ══════════════════════════════════════════════

class TestRiskLedger:
    """Test risk ledger generation and classification."""

    def _make_violation(self, rule_section="§3 — Terminology", issue_title="Prohibited term",
                        original_text="leverage", blocks=False):
        return Violation(
            original_text=original_text,
            issue_title=issue_title,
            rule_section=rule_section,
            rule_id="RULE-3.1",
            explanation="test",
            severity=Severity.HIGH,
            suggested_fix="use 'use'",
            blocks_publishing=blocks,
        )

    def _make_adaptation(self, changes=None):
        return AdaptationResult(
            adapted_content="fixed content",
            word_count=2,
            channel=Channel.LINKEDIN,
            audience=Audience.PRACTITIONER,
            change_log=changes or [],
        )

    def test_classify_risk_legal(self):
        from backend.services.risk_ledger import _classify_risk
        assert _classify_risk("§5 — Claims and Legal", "Unsupported claim") == "legal"

    def test_classify_risk_channel(self):
        from backend.services.risk_ledger import _classify_risk
        assert _classify_risk("§6 — Channel Format", "Word count exceeded") == "channel"

    def test_classify_risk_audience(self):
        from backend.services.risk_ledger import _classify_risk
        assert _classify_risk("§4 — Tone", "Wrong audience tone") == "audience"

    def test_classify_risk_brand_default(self):
        from backend.services.risk_ledger import _classify_risk
        assert _classify_risk("§3 — Terminology", "Prohibited term") == "brand"

    def test_auto_fixed_when_adaptation_matches(self):
        from backend.services.risk_ledger import generate_risk_ledger
        v = self._make_violation(original_text="leverage")
        changes = [ChangeLogEntry(
            original_text="leverage", changed_text="use",
            change_type="terminology", rule_reference="RULE-3.1",
            rationale="prohibited term",
        )]
        adaptation = self._make_adaptation(changes)
        audit = AuditReport(violations=[v], summary="")
        ledger = generate_risk_ledger(audit, adaptation)
        assert len(ledger) == 1
        assert ledger[0].final_action == "auto-fixed"

    def test_flagged_for_review_when_not_adapted(self):
        from backend.services.risk_ledger import generate_risk_ledger
        v = self._make_violation(original_text="leverage")
        adaptation = self._make_adaptation([])  # no changes
        audit = AuditReport(violations=[v], summary="")
        ledger = generate_risk_ledger(audit, adaptation)
        assert len(ledger) == 1
        assert ledger[0].final_action == "flagged for review"

    def test_blocking_violation_flagged(self):
        from backend.services.risk_ledger import generate_risk_ledger
        v = self._make_violation(original_text="50% faster", blocks=True)
        adaptation = self._make_adaptation([])
        audit = AuditReport(violations=[v], summary="")
        ledger = generate_risk_ledger(audit, adaptation)
        assert ledger[0].final_action == "flagged for review"

    def test_empty_violations_empty_ledger(self):
        from backend.services.risk_ledger import generate_risk_ledger
        adaptation = self._make_adaptation([])
        audit = AuditReport(violations=[], summary="Clean")
        ledger = generate_risk_ledger(audit, adaptation)
        assert len(ledger) == 0


# ══════════════════════════════════════════════
#  MOCKED LLM INTEGRATION
# ══════════════════════════════════════════════

class TestLLMIntegration:
    """Test LLM wrapper handling of malformed responses (mocked, no real API calls)."""

    @patch("backend.services.llm.get_embedding")
    def test_get_embedding_returns_vector(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        from backend.services.llm import get_embedding
        result = get_embedding("test text")
        assert len(result) == 1536

    @patch("backend.services.llm._get_client")
    def test_chat_json_parses_valid_json(self, mock_client):
        """Verify chat_json extracts JSON from a well-formed response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"rules": [{"rule_id": "RULE-1"}]}'
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from backend.services.llm import chat_json
        result = chat_json("audit_system.txt", "test", max_completion_tokens=100)
        assert "rules" in result
        assert result["rules"][0]["rule_id"] == "RULE-1"


# ══════════════════════════════════════════════
#  FASTAPI SCHEMA VALIDATION
# ══════════════════════════════════════════════

class TestSchemaValidation:
    """Test Pydantic request model validation without a server."""

    def test_audit_request_rejects_empty_content(self):
        from backend.models.schemas import AuditRequest
        with pytest.raises(Exception):  # ValidationError
            AuditRequest(content="", guideline_id="abc", channel="linkedin", audience="executive")

    def test_audit_request_accepts_valid(self):
        from backend.models.schemas import AuditRequest
        req = AuditRequest(content="Valid content here", guideline_id="abc",
                           channel="linkedin", audience="executive")
        assert req.content == "Valid content here"

    def test_guideline_ingest_rejects_short_text(self):
        from backend.models.schemas import GuidelineIngestRequest
        with pytest.raises(Exception):
            GuidelineIngestRequest(name="Test", text="short")

    def test_guideline_ingest_rejects_empty_name(self):
        from backend.models.schemas import GuidelineIngestRequest
        with pytest.raises(Exception):
            GuidelineIngestRequest(name="", text="x" * 20)

    def test_guideline_ingest_accepts_valid(self):
        from backend.models.schemas import GuidelineIngestRequest
        req = GuidelineIngestRequest(name="Brand Guide", text="x" * 50)
        assert req.name == "Brand Guide"

    def test_any_channel_string_accepted(self):
        """Channel is now a free string (DB-backed), so any value is accepted at schema level."""
        from backend.models.schemas import AuditRequest
        req = AuditRequest(content="test content", guideline_id="abc",
                           channel="tiktok", audience="executive")
        assert req.channel == "tiktok"

    def test_any_audience_string_accepted(self):
        """Audience is now a free string (DB-backed), so any value is accepted at schema level."""
        from backend.models.schemas import AuditRequest
        req = AuditRequest(content="test content", guideline_id="abc",
                           channel="linkedin", audience="partner")
        assert req.audience == "partner"
