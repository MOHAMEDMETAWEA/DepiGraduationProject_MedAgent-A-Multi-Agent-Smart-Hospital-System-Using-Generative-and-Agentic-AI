"""Unit tests for Post-LLM Safety Gate (forbidden phrase rewriter + triage consistency).

These exercise the pure-logic surface of the gate so they can run without an LLM.
"""

from __future__ import annotations

from app.ai.safety.post_llm_gate import PostLLMSafetyGate


class TestForbiddenPhraseRewriter:
    """Stage 3.2 — prescriptive language must be rewritten to advisory."""

    def test_rewrites_you_should_take(self):
        text = "You should take ibuprofen 400mg every 6 hours."
        safe, count = PostLLMSafetyGate._rewrite_forbidden_phrases(text)
        assert "you should take" not in safe.lower()
        assert count >= 1

    def test_rewrites_dose_pattern_to_no_self_medicate(self):
        text = "Take 500mg of acetaminophen now."
        safe, count = PostLLMSafetyGate._rewrite_forbidden_phrases(text)
        assert "do not self-medicate" in safe
        assert count >= 1

    def test_rewrites_definitive_diagnosis_language(self):
        text = "This is definitely strep throat."
        safe, count = PostLLMSafetyGate._rewrite_forbidden_phrases(text)
        assert "this may be" in safe.lower()
        assert "definitely" not in safe.lower()
        assert count == 1

    def test_passes_through_advisory_language_untouched(self):
        text = "Consider discussing your symptoms with a doctor."
        safe, count = PostLLMSafetyGate._rewrite_forbidden_phrases(text)
        assert safe == text
        assert count == 0

    def test_counts_multiple_independent_rewrites(self):
        text = "You must take antibiotics. This is definitely an infection."
        _, count = PostLLMSafetyGate._rewrite_forbidden_phrases(text)
        assert count >= 2


class TestTriageConsistency:
    """Stage 3.3 — recommended action must match triage urgency."""

    def test_emergency_with_emergency_action_is_consistent(self):
        text = "This is an emergency — call 911 immediately."
        assert PostLLMSafetyGate._check_triage_consistency(text, "emergency") is True

    def test_emergency_with_only_routine_action_is_inconsistent(self):
        text = "Just monitor at home and watch for changes."
        assert PostLLMSafetyGate._check_triage_consistency(text, "emergency") is False

    def test_routine_with_self_care_is_consistent(self):
        text = "Self-care at home should help with these mild symptoms."
        assert PostLLMSafetyGate._check_triage_consistency(text, "routine") is True

    def test_no_triage_level_always_consistent(self):
        text = "Some advice."
        assert PostLLMSafetyGate._check_triage_consistency(text, "") is True

    def test_arabic_emergency_action_recognized(self):
        text = "اذهب للطوارئ فوراً."
        # Either consistent (if Arabic emergency action is in the map) or not flagged as risky
        result = PostLLMSafetyGate._check_triage_consistency(text, "emergency")
        assert result is True
