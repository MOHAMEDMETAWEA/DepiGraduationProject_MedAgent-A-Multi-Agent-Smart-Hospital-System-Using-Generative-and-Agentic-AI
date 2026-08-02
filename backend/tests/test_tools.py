"""Tests for Phase 2 tools: medication, mental health, red flags, triage, PII."""

import pytest
from app.ai.agent.pii import scrub_pii
from app.ai.tools.medication import CheckMedicationTool, MedicationChecker, MedicationInput
from app.ai.tools.mental_health import (
    MentalHealthInput,
    MentalHealthScreener,
    ScreenMentalHealthTool,
)
from app.ai.tools.red_flag_detector import DetectRedFlagsTool, RedFlagDetector
from app.ai.tools.triage_scorer import TriageScorer

# ── PII Scrub ──


class TestPiiScrub:
    def test_scrubs_phone(self):
        assert "[PHONE]" in scrub_pii("Call me at 01012345678")
        assert "[PHONE]" in scrub_pii("My number is 01234567890")

    def test_scrubs_email(self):
        assert "[EMAIL]" in scrub_pii("Email me at test@example.com")

    def test_scrubs_national_id(self):
        # 14-digit Egyptian ID starting with 2 or 3
        result = scrub_pii("National ID 29801010101234 please")
        assert "[ID]" in result or "[PHONE]" in result  # either mask is ok

    def test_preserves_medical_text(self):
        text = "I have chest pain radiating to left arm"
        assert scrub_pii(text) == text

    def test_empty_text(self):
        assert scrub_pii("") == ""


# ── Medication Checker ──


class TestMedicationChecker:
    def test_known_interaction(self):
        checker = MedicationChecker()
        result = checker.check(["warfarin"], "aspirin")
        assert len(result["interactions"]) > 0
        assert result["interactions"][0]["severity"] == "major"

    def test_safe_combination(self):
        checker = MedicationChecker()
        result = checker.check(["metformin"], "acetaminophen")
        assert len(result["interactions"]) == 0

    def test_allergy_conflict(self):
        checker = MedicationChecker()
        result = checker.check(["metformin"], "penicillin", ["penicillin"])
        assert len(result["allergy_conflicts"]) > 0

    def test_arabic_drug_name(self):
        checker = MedicationChecker()
        result = checker.check(["وارفارين"], "ibuprofen")
        assert len(result["interactions"]) > 0

    def test_unknown_medication(self):
        checker = MedicationChecker()
        result = checker.check([], "xyz_unknown_drug")
        assert "error" in result

    def test_tool_schema(self):
        tool = CheckMedicationTool()
        assert tool.name == "check_medication_interactions"
        assert tool.input_schema == MedicationInput

    @pytest.mark.asyncio(loop_scope="session")
    async def test_tool_run(self):
        tool = CheckMedicationTool()
        result = await tool.run(
            MedicationInput(current_medications=["warfarin"], new_medication="aspirin")
        )
        assert result["total_warnings"] > 0


# ── Mental Health Screener ──


class TestMentalHealthScreener:
    def test_phq9_severe(self):
        screener = MentalHealthScreener()
        result = screener.screen([3] * 9, "phq9")
        assert result["score"] == 27
        assert result["severity"] == "severe"
        assert result["has_suicidality"] is True

    def test_phq9_mild(self):
        # Score 6 = mild (5-9 range)
        result = MentalHealthScreener().screen([1, 1, 1, 1, 1, 1, 0, 0, 0], "phq9")
        assert result["severity"] == "mild"

    def test_gad7_moderate(self):
        result = MentalHealthScreener().screen([2, 2, 2, 1, 1, 1, 1], "gad7")
        assert result["severity"] == "moderate"

    def test_phq9_suicidality_escalation(self):
        result = MentalHealthScreener().screen([0, 0, 0, 0, 0, 0, 0, 0, 2], "phq9")
        assert result["has_suicidality"] is True
        assert result["crisis_resources"] is not None

    def test_no_suicidality(self):
        result = MentalHealthScreener().screen([0] * 9, "phq9")
        assert result["has_suicidality"] is False

    def test_wrong_response_count(self):
        result = MentalHealthScreener().screen([1, 2], "phq9")
        assert "error" in result

    def test_tool_schema(self):
        tool = ScreenMentalHealthTool()
        assert tool.name == "screen_mental_health"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_tool_run(self):
        tool = ScreenMentalHealthTool()
        result = await tool.run(MentalHealthInput(responses=[0] * 9, screening_type="phq9"))
        assert result["score"] == 0


# ── Red Flag Detector ──


class TestRedFlagDetector:
    def test_emergency_chest_pain(self):
        detector = RedFlagDetector()
        result = detector.detect("I have crushing chest pain radiating to my arm")
        assert result["has_red_flag"] is True
        assert result["severity"] == "emergency"

    def test_arabic_stroke(self):
        detector = RedFlagDetector()
        result = detector.detect("عندي ضعف في جهة واحدة من جسمي")
        assert result["has_red_flag"] is True

    def test_no_red_flag(self):
        detector = RedFlagDetector()
        result = detector.detect("I have a mild headache since yesterday")
        assert result["has_red_flag"] is False

    def test_suicidal_escalation(self):
        detector = RedFlagDetector()
        result = detector.detect("I want to kill myself")
        assert result["severity"] == "emergency"

    def test_tool_schema(self):
        tool = DetectRedFlagsTool()
        assert tool.name == "detect_red_flags"


# ── Triage Scorer ──


class TestTriageScorer:
    def test_emergency_chest_pain(self):
        scorer = TriageScorer()
        result = scorer.score(["chest pain", "radiating to arm"])
        assert result["level"] == "emergency"
        assert result["score"] >= 80

    def test_urgent_fever(self):
        scorer = TriageScorer()
        result = scorer.score(["fever", "39"])
        assert result["level"] == "urgent"

    def test_routine_mild(self):
        scorer = TriageScorer()
        result = scorer.score(["mild headache"])
        assert result["level"] == "routine"

    def test_red_flag_override(self):
        scorer = TriageScorer()
        result = scorer.score(["mild headache"], red_flags_detected=True)
        assert result["level"] == "emergency"
        assert result["score"] == 100

    def test_age_adjustment_infant(self):
        scorer = TriageScorer()
        result = scorer.score(["mild headache"], age=0)
        assert result["score"] > 10  # Should be higher due to infant adjustment

    def test_comorbidity_adjustment(self):
        scorer = TriageScorer()
        baseline = scorer.score(["mild headache"])
        with_diabetes = scorer.score(["mild headache"], comorbidities=["diabetes"])
        assert with_diabetes["score"] >= baseline["score"]

    def test_arabic_emergency(self):
        scorer = TriageScorer()
        result = scorer.score(["ألم", "صدر", "يمتد"])
        assert result["level"] == "emergency"

    def test_score_capped_at_100(self):
        scorer = TriageScorer()
        result = scorer.score(
            ["chest pain", "radiating"], age=0, comorbidities=["diabetes", "heart disease"]
        )
        assert result["score"] <= 100
