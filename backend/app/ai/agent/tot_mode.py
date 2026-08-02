"""
Tree-of-Thought Mode — وضع التشخيص التفريقي متعدد الفروع

لما الأعراض تكون ambiguous والـ triage urgent، الـ Agent بيحوّل لـ ToT mode
بدل ReAct loop العادي. الفكرة: بدل خط تفكير واحد، يولّد 3 احتمالات تشخيص،
يسجل كل واحد، ويختار أفضل 2.

قاعدة الاختيار من §8.8.3:
  if red_flags.is_emergency  → EMERGENCY_FAST_PATH  (مافيش تفكير أصلاً)
  elif triage=='urgent' and confidence < 0.7 → TOT_MODE
  else → REACT_MODE
"""

from __future__ import annotations

from typing import Any


class ToTOrchestrator:
    """
    منسق وضع Tree-of-Thought — بيقرر ويدير عملية التشخيص التفريقي.

    الخطوات:
    1. يقرر إذا كان ToT مناسب (mode_selection)
    2. يجمع الأعراض والتاريخ من المحادثة
    3. يسترجع المصادر من RAG
    4. يشغل tot_differential_diagnosis tool
    5. يرجع الفروع للعرض
    """

    @staticmethod
    def should_use_tot(
        triage_level: str | None,
        red_flag_severity: str = "none",
        top_confidence: float = 1.0,
    ) -> bool:
        """
        يحدد إذا كان لازم نستخدم Tree-of-Thought ولا لأ.

        الشروط (كلها لازم تتحقق):
        1. triage_level == "urgent" (مش emergency — emergency ليها fast path)
        2. مفيش red flags emergency (red flags → fast path الأول)
        3. درجة الثقة في التشخيص الحالي أقل من 0.7

        Returns:
            True لو ToT مناسب، False لو نمشي ReAct عادي
        """
        # Emergency → fast path (مش محتاجين ToT أصلاً)
        if red_flag_severity == "emergency":
            return False

        # لازم urgent
        if triage_level != "urgent":
            return False

        # لازم الثقة منخفضة
        return not top_confidence >= 0.7

    @staticmethod
    def build_tot_context(
        conversation_history: list[dict[str, str]],
        patient_age: int | None = None,
        patient_conditions: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        يبني سياق ToT من المحادثة.

        بيستخرج:
        - symptoms: كل حاجة المريض قالها عن الأعراض
        - history: العمر + الأمراض المزمنة + الأدوية

        Returns:
            (symptoms, history) — جاهزين لـ tot_differential_diagnosis
        """
        # نجمع كل رسايل المريض
        patient_messages = [
            msg.get("content", "") for msg in conversation_history if msg.get("role") == "user"
        ]

        symptoms = " ".join(patient_messages) if patient_messages else "No symptoms reported"

        # نبني التاريخ المرضي
        history_parts = []
        if patient_age is not None:
            history_parts.append(f"Age: {patient_age}")
        if patient_conditions:
            history_parts.append(f"Conditions: {', '.join(patient_conditions)}")

        history = "; ".join(history_parts) if history_parts else "No history available"

        return symptoms, history

    @staticmethod
    def format_branches_for_ui(
        tot_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        ينسق نتيجة ToT للعرض في الواجهة.

        بيضيف metadata زي الألوان والأيقونات لكل فرع.
        """
        branches = tot_result.get("branches", [])

        formatted = []
        for branch in branches:
            urgency = branch.get("urgency", "routine")
            formatted.append(
                {
                    "hypothesis": branch.get("hypothesis", "Unknown"),
                    "probability": branch.get("probability", 0),
                    "reasoning": branch.get("reasoning", ""),
                    "supporting_evidence": branch.get("supporting_evidence", []),
                    "contradicting_evidence": branch.get("contradicting_evidence", []),
                    "recommended_action": branch.get("recommended_action", ""),
                    "urgency": urgency,
                    # لون حسب الـ urgency
                    "color": (
                        "#d92d20"
                        if urgency == "emergency"
                        else "#f79009"
                        if urgency == "urgent"
                        else "#12b76a"
                    ),
                }
            )

        return {
            "mode": "tree_of_thought",
            "branches": formatted,
            "count": len(formatted),
        }
