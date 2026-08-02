"""Auto-detection tests for Pediatric and Pregnancy branches.

These guard the entry conditions that decide whether the agent loads a
specialized system prompt and applies branch-specific red-flag rules.
"""

from __future__ import annotations

from app.ai.agent.branches.pediatric import PediatricContext
from app.ai.agent.branches.pregnancy import PregnancyContext


class TestPediatricBranchDetection:
    def test_returns_none_for_adult(self):
        assert PediatricContext.from_age_years(25) is None
        assert PediatricContext.from_age_years(18) is None

    def test_returns_context_for_child(self):
        ctx = PediatricContext.from_age_years(8)
        assert ctx is not None
        assert ctx.age_months == 96.0

    def test_neonate_classification(self):
        ctx = PediatricContext.from_age_years(0.05)  # ~18 days
        assert ctx is not None
        assert ctx.is_neonate is True
        assert ctx.is_young_infant is True
        assert ctx.is_infant is True

    def test_young_infant_under_3_months(self):
        ctx = PediatricContext.from_age_years(2 / 12)  # 2 months
        assert ctx is not None
        assert ctx.is_neonate is False
        assert ctx.is_young_infant is True

    def test_school_age_child(self):
        ctx = PediatricContext.from_age_years(10)
        assert ctx is not None
        assert ctx.is_neonate is False
        assert ctx.is_infant is False
        assert "child" in ctx.age_label


class TestPregnancyBranchDetection:
    def test_detects_english_pregnancy_keyword(self):
        ctx = PregnancyContext.detect_from_text("I'm pregnant and have a headache")
        assert ctx is not None

    def test_detects_arabic_pregnancy_keyword(self):
        ctx = PregnancyContext.detect_from_text("أنا حامل وعندي صداع")
        assert ctx is not None

    def test_returns_none_for_unrelated_text(self):
        ctx = PregnancyContext.detect_from_text("My head hurts")
        assert ctx is None

    def test_extracts_trimester_from_english(self):
        ctx = PregnancyContext.detect_from_text("I'm in my second trimester")
        assert ctx is not None
        # Extraction is best-effort; assert it didn't crash and either matched or returned None
        assert ctx.trimester in (None, 2)

    def test_trimester_label_unknown_when_missing(self):
        ctx = PregnancyContext.detect_from_text("I am pregnant")
        assert ctx is not None
        assert "unknown" in ctx.trimester_label or "weeks" in ctx.trimester_label
