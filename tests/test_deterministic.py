"""Pytest tests for deterministic auditor and approval logic.

These tests do NOT call Azure OpenAI — they test pure deterministic logic.
"""

import pytest
from backend.services.deterministic_auditor import run_deterministic_audit
from backend.models.schemas import (
    Severity,
    Channel,
    AuditReport,
    Violation,
    ReviewerOpinion,
    ReviewerVerdict,
    PublishStatus,
)


# ══════════════════════════════════════════════
#  PROHIBITED TERM DETECTION
# ══════════════════════════════════════════════

class TestProhibitedTerms:
    def test_ai_powered_flagged(self):
        violations = run_deterministic_audit("Axion is an AI-powered platform.")
        rule_ids = [v.rule_id for v in violations]
        assert "RULE-2.2" in rule_ids

    def test_ai_assisted_not_flagged(self):
        violations = run_deterministic_audit("Axion is an AI-assisted platform.")
        rule_ids = [v.rule_id for v in violations]
        assert "RULE-2.2" not in rule_ids

    def test_leverage_flagged(self):
        violations = run_deterministic_audit("We leverage machine learning to help teams.")
        matches = [v for v in violations if v.rule_id == "RULE-3.1"]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.CRITICAL

    def test_leverages_flagged(self):
        violations = run_deterministic_audit("The platform leverages AI.")
        matches = [v for v in violations if v.rule_id == "RULE-3.1"]
        assert len(matches) >= 1

    def test_seamlessly_flagged(self):
        violations = run_deterministic_audit("It integrates seamlessly with your CRM.")
        matches = [v for v in violations if v.rule_id == "RULE-3.5"]
        assert len(matches) >= 1

    def test_industry_leading_flagged(self):
        violations = run_deterministic_audit("Our industry-leading accuracy.")
        matches = [v for v in violations if v.rule_id == "RULE-3.4"]
        assert len(matches) >= 1
        assert matches[0].severity == Severity.CRITICAL
        assert matches[0].blocks_publishing is True

    def test_best_in_class_flagged(self):
        violations = run_deterministic_audit("Best-in-class forecasting.")
        matches = [v for v in violations if v.rule_id == "RULE-3.4"]
        assert len(matches) >= 1

    def test_revolutionary_flagged(self):
        violations = run_deterministic_audit("A revolutionary approach to revenue.")
        matches = [v for v in violations if v.rule_id == "RULE-3.3"]
        assert len(matches) >= 1

    def test_game_changing_flagged(self):
        violations = run_deterministic_audit("A game-changing improvement.")
        matches = [v for v in violations if v.rule_id == "RULE-3.3"]
        assert len(matches) >= 1

    def test_robust_flagged(self):
        violations = run_deterministic_audit("A robust solution for enterprises.")
        matches = [v for v in violations if v.rule_id == "RULE-3.6"]
        assert len(matches) >= 1

    def test_empower_flagged(self):
        violations = run_deterministic_audit("We empower revenue teams.")
        matches = [v for v in violations if v.rule_id == "RULE-3.8"]
        assert len(matches) >= 1

    def test_synergy_flagged(self):
        violations = run_deterministic_audit("Synergistic outcomes across teams.")
        matches = [v for v in violations if v.rule_id == "RULE-3.2"]
        assert len(matches) >= 1


# ══════════════════════════════════════════════
#  PROHIBITED CTA DETECTION
# ══════════════════════════════════════════════

class TestProhibitedCTAs:
    def test_learn_more_flagged(self):
        violations = run_deterministic_audit("Learn more about our platform.")
        matches = [v for v in violations if "Learn more" in v.issue_title]
        assert len(matches) >= 1

    def test_click_here_flagged(self):
        violations = run_deterministic_audit("Click here to get started.")
        matches = [v for v in violations if "Click here" in v.issue_title]
        assert len(matches) >= 1

    def test_free_trial_flagged(self):
        violations = run_deterministic_audit("Get your free trial today.")
        matches = [v for v in violations if "ree trial" in v.issue_title]
        assert len(matches) >= 1

    def test_approved_cta_not_flagged(self):
        violations = run_deterministic_audit("Book a demo today.")
        cta_violations = [v for v in violations if "CTA" in v.issue_title]
        assert len(cta_violations) == 0


# ══════════════════════════════════════════════
#  CHANNEL LENGTH CHECKS
# ══════════════════════════════════════════════

class TestChannelLengthChecks:
    def test_linkedin_over_150_flagged(self):
        long_content = " ".join(["word"] * 160)
        violations = run_deterministic_audit(long_content, channel=Channel.LINKEDIN)
        length_violations = [v for v in violations if "word limit" in v.issue_title.lower()]
        assert len(length_violations) >= 1

    def test_linkedin_under_150_ok(self):
        short_content = " ".join(["word"] * 100)
        violations = run_deterministic_audit(short_content, channel=Channel.LINKEDIN)
        length_violations = [v for v in violations if "word limit" in v.issue_title.lower()]
        assert len(length_violations) == 0

    def test_email_over_300_flagged(self):
        long_content = " ".join(["word"] * 350)
        violations = run_deterministic_audit(long_content, channel=Channel.EMAIL)
        length_violations = [v for v in violations if "word limit" in v.issue_title.lower()]
        assert len(length_violations) >= 1

    def test_event_abstract_under_75_flagged(self):
        short_content = " ".join(["word"] * 50)
        violations = run_deterministic_audit(short_content, channel=Channel.EVENT_ABSTRACT)
        length_violations = [v for v in violations if "minimum" in v.issue_title.lower()]
        assert len(length_violations) >= 1


# ══════════════════════════════════════════════
#  CLEAN CONTENT
# ══════════════════════════════════════════════

class TestCleanContent:
    def test_clean_content_no_violations(self):
        clean = (
            "Axion is an AI-assisted revenue intelligence platform that helps "
            "sales teams identify at-risk accounts. Book a demo today."
        )
        violations = run_deterministic_audit(clean)
        assert len(violations) == 0, f"Unexpected violations: {[v.issue_title for v in violations]}"


# ══════════════════════════════════════════════
#  APPROVAL / PUBLISH STATUS LOGIC
# ══════════════════════════════════════════════

class TestPublishStatusLogic:
    """Test the _determine_publish_status function from approval.py."""

    def test_no_violations_all_approved(self):
        from backend.services.approval import _determine_publish_status
        audit = AuditReport(violations=[], critical_count=0, high_count=0, medium_count=0, low_count=0, summary="")
        reviewers = [
            ReviewerOpinion(reviewer_name="Brand", verdict=ReviewerVerdict.APPROVED, top_concerns=[], reason="OK", confidence_score=0.9),
            ReviewerOpinion(reviewer_name="Legal", verdict=ReviewerVerdict.APPROVED, top_concerns=[], reason="OK", confidence_score=0.9),
        ]
        assert _determine_publish_status(audit, reviewers) == PublishStatus.APPROVED

    def test_critical_violation_not_publishable(self):
        from backend.services.approval import _determine_publish_status
        audit = AuditReport(violations=[], critical_count=1, high_count=0, medium_count=0, low_count=0, summary="")
        reviewers = [
            ReviewerOpinion(reviewer_name="Brand", verdict=ReviewerVerdict.APPROVED, top_concerns=[], reason="OK", confidence_score=0.9),
        ]
        assert _determine_publish_status(audit, reviewers) == PublishStatus.NOT_PUBLISHABLE

    def test_reviewer_rejected_not_publishable(self):
        from backend.services.approval import _determine_publish_status
        audit = AuditReport(violations=[], critical_count=0, high_count=0, medium_count=0, low_count=0, summary="")
        reviewers = [
            ReviewerOpinion(reviewer_name="Legal", verdict=ReviewerVerdict.REJECTED, top_concerns=["Claim issue"], reason="No", confidence_score=0.8),
        ]
        assert _determine_publish_status(audit, reviewers) == PublishStatus.NOT_PUBLISHABLE

    def test_conditional_reviewer_approved_with_conditions(self):
        from backend.services.approval import _determine_publish_status
        audit = AuditReport(violations=[], critical_count=0, high_count=0, medium_count=0, low_count=0, summary="")
        reviewers = [
            ReviewerOpinion(reviewer_name="Brand", verdict=ReviewerVerdict.CONDITIONAL, top_concerns=["Minor"], reason="Almost", confidence_score=0.7),
        ]
        assert _determine_publish_status(audit, reviewers) == PublishStatus.APPROVED_WITH_CONDITIONS

    def test_high_violations_approved_with_conditions(self):
        from backend.services.approval import _determine_publish_status
        audit = AuditReport(violations=[], critical_count=0, high_count=3, medium_count=0, low_count=0, summary="")
        reviewers = [
            ReviewerOpinion(reviewer_name="Brand", verdict=ReviewerVerdict.APPROVED, top_concerns=[], reason="OK", confidence_score=0.9),
        ]
        assert _determine_publish_status(audit, reviewers) == PublishStatus.APPROVED_WITH_CONDITIONS


# ══════════════════════════════════════════════
#  MERGE LOGIC (deterministic + LLM violations)
# ══════════════════════════════════════════════

class TestMergeViolations:
    def _v(self, rule_id, text, source="llm"):
        return Violation(original_text=text, issue_title=f"Test", rule_section="§T",
                         rule_id=rule_id, explanation="t", severity=Severity.HIGH,
                         suggested_fix="f", blocks_publishing=False, source=source)

    def test_different_rules_both_kept(self):
        from backend.services.approval import _merge_violations
        merged = _merge_violations([self._v("R1","leverage","deterministic")], [self._v("R2","seamlessly")])
        assert len(merged) == 2

    def test_exact_dup_keeps_deterministic(self):
        from backend.services.approval import _merge_violations
        merged = _merge_violations([self._v("R1","leverage","deterministic")], [self._v("R1","leverage")])
        assert len(merged) == 1
        assert merged[0].source == "deterministic"

    def test_substring_dup_removed(self):
        from backend.services.approval import _merge_violations
        merged = _merge_violations([self._v("R1","AI-powered","deterministic")], [self._v("R1","AI-powered platform")])
        assert len(merged) == 1

    def test_colon_in_text_safe(self):
        from backend.services.approval import _merge_violations
        merged = _merge_violations([self._v("R1","claim: 50%","deterministic")], [self._v("R1","claim: 50%")])
        assert len(merged) == 1

    def test_source_field_on_deterministic(self):
        viols = run_deterministic_audit("We leverage AI.")
        assert any(v.source == "deterministic" for v in viols)
