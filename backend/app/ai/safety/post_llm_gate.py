"""
Post-LLM Safety Gate — بوابة الأمان بعد توليد الرد (Stage 3)

بعد ما الـ Agent يخلص ReAct loop ويطلع رد نهائي، البوابة دي بتمسك الرد
وتشغله على مدقق الهلاوس. لو درجة الهلاوس أعلى من الحد المسموح، الرد بيتعدل
أو الجمل غير المدعومة بتتمسح قبل ما يوصل للمريض.

المبدأ: Fail closed — لو البوابة مقدرتش تشتغل أو الـ verifier مش متاح،
بنضيف تحذير للمريض بدل ما نسكت. سلامة المريض أولاً.

بعد التدقيق، النتيجة بتتسجل في جدول safety_assessments عشان نتابع أداء النظام.

Stage 3 checks:
  1. Hallucination detection — كل claim طبي لازم يكون مدعوم بمصدر
  2. Forbidden phrase rewriting — لغة وصفية (إرشادات صريحة) → لغة استشارية
  3. Triage consistency — التأكد من تطابق التوصية النهائية مع نتيجة التصنيف
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from app.ai.tools.verify_no_hallucination import HallucinationVerifier


@dataclass
class SafetyGateResult:
    """
    نتيجة مرور الرد من بوابة الأمان.

    action:
        'pass' → الرد سليم، يعدي زي ما هو
        'rewrite' → الرد اتعدل — claims غير مدعومة اتعاد صياغتها أو forbidden phrases اتبدلت
        'flag' → الرد خطير — محتاج مراجعة بشرية (admin)

    original_text: الرد الأصلي قبل التدقيق
    safe_text: الرد النهائي اللي يوصل للمريض (بعد التعديل لو حصل)
    assessment: dict بيحتوي على نتيجة التدقيق كاملة (للحفظ في الداتابيز)
    forbidden_phrases_rewritten: عدد العبارات المحظورة اللي اتعادت صياغتها
    triage_consistent: هل التوصية النهائية متطابقة مع نتيجة التصنيف؟
    """

    action: str  # pass | rewrite | flag
    original_text: str
    safe_text: str
    assessment: dict[str, Any]
    forbidden_phrases_rewritten: int = 0
    triage_consistent: bool = True


class PostLLMSafetyGate:
    """
    بوابة الأمان — بتنسق بين الـ Verifier ومخرج الـ Agent.

    بتستقبل:
    - assistant_text: الرد النهائي اللي الـ Agent عايز يبعتوا
    - sources: المصادر اللي استخدمها (من RAG)
    - triage_info: نتيجة التصنيف (للتحقق من consistency)

    وبتعمل:
    1. تشغل verifier.verify() على الرد
    2. تعيد صياغة forbidden phrases (لغة إرشادية → استشارية)
    3. تتأكد من تطابق التوصية مع triage
    4. ترجع SafetyGateResult بالرد الآمن والقرار
    """

    # Short factual notes — the previous "⚠️ Please consult a licensed
    # physician before acting" / "please discuss with a doctor" footers
    # were appearing on every routine reply and made the product feel
    # paranoid. The same legal effect is achieved with the one-line
    # "preliminary triage" framing the user sees in the vision card and
    # the main system prompt — duplicating it here added noise without
    # adding safety. We keep a quiet inline note for transparency when
    # the verifier flagged something, but the assertive deflection
    # language is gone.
    VERIFIER_UNAVAILABLE_DISCLAIMER = (
        "\n\n_ملاحظة: لم نتمكّن من التحقق التلقائي من بعض المعلومات في الرد._"
    )

    UNCERTAINTY_DISCLAIMER = "\n\n_ملاحظة: بعض النقاط في الرد لم تُتحقق بالكامل من المراجع._"

    # ── Stage 3.2: Forbidden phrase patterns ──
    # لغة إرشادية صريحة (وصفات، جرعات، تعليمات قطعية) لازم تتحول للغة استشارية

    FORBIDDEN_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # English prescriptive → advisory
        (r"\byou should take\b", "consider discussing with your doctor whether"),
        (r"\byou must take\b", "it may be worth asking your doctor about"),
        (r"\byou need to take\b", "your doctor may recommend"),
        (r"\bstart taking\b", "discuss with your doctor about starting"),
        (
            r"\btake (\d+)\s*(mg|g|mcg|ml|IU)\b",
            r"your doctor may prescribe a dose such as \1 \2 — do not self-medicate",
        ),
        (r"\bprescribe\b", "a doctor may consider"),
        (r"\byou are diagnosed with\b", "this is consistent with (not a diagnosis)"),
        (r"\byou have (a|an)\b(?!emergency|doctor|medical)", r"this could indicate \1possible"),
        (r"\bthis is definitely\b", "this may be"),
        (r"\bit is certain that\b", "current evidence suggests"),
        # Arabic prescriptive → advisory
        (r"\bيجب أن تأخذ\b", "يُفضل استشارة الطبيب حول إمكانية استخدام"),
        (r"\bلازم تاخد\b", "يفضل استشارة الطبيب حول"),
        (
            r"\bخذ (\d+)\s*(مجم|جم|مل)\b",
            r"قد يصف الطبيب جرعة مثل \1 \2 — لا تتناول أدوية بدون استشارة",
        ),
        (r"\bأنت مصاب بـ\b", "هذا قد يشير إلى احتمالية"),
        (r"\bشخّصت بـ\b", "هذا يتوافق مع (وليس تشخيصاً)"),
        (r"\bهذا بالتأكيد\b", "هذا قد يكون"),
        (r"\bالعلاج هو\b", "من الخيارات العلاجية المحتملة"),
    ]

    # ── Stage 3.3: Triage consistency mapping ──
    # التوصية النهائية لازم تكون متسقة مع مستوى triage

    TRIAGE_ACTION_MAP: ClassVar[dict[str, list[str]]] = {
        "emergency": [
            "go to emergency",
            "call ambulance",
            "visit er",
            "اذهب للطوارئ",
            "اتصل بالإسعاف",
            "توجه للمستشفى",
        ],
        "urgent": [
            "see a doctor",
            "book appointment",
            "visit clinic",
            "راجع طبيب",
            "احجز موعد",
            "زور عيادة",
        ],
        "routine": [
            "monitor at home",
            "self-care",
            "watch for changes",
            "راقب في المنزل",
            "عناية ذاتية",
            "تابع الأعراض",
        ],
    }

    def __init__(self, verifier: HallucinationVerifier):
        """
        بينشئ بوابة الأمان.

        verifier: instance من HallucinationVerifier — جاهز ومجهز بـ LLM provider
        """
        self._verifier = verifier

    async def check(
        self,
        assistant_text: str,
        sources: list[dict[str, str]],
        triage_level: str | None = None,
    ) -> SafetyGateResult:
        """
        يشغل بوابة الأمان على رد الـ Agent.

        بيمرر الرد والمصادر للـ verifier، وبياخد القرار:
        - pass: الرد سليم، يعدي
        - rewrite: نمسح الجمل غير المدعومة ونضيف تحذير
        - flag: الرد خطير جداً (score > 0.7) — محتاج admin review

        Args:
            assistant_text: الرد النهائي من الـ Agent
            sources: المصادر الطبية المستخدمة
            triage_level: نتيجة التصنيف (emergency/urgent/routine) للتحقق من consistency
        """
        text = assistant_text
        forbidden_rewrites = 0
        triage_consistent = True

        # ── Stage 3.2: Forbidden phrase rewriting (always runs first) ──
        text, forbidden_rewrites = self._rewrite_forbidden_phrases(text)

        # ── Stage 3.1: Hallucination check ──
        try:
            assessment = await self._verifier.verify(
                assistant_message=text,
                sources=sources,
            )
        except Exception:
            # لو الـ verifier فشل — fail closed: نضيف تحذير بس
            return SafetyGateResult(
                action="pass",
                original_text=assistant_text,
                safe_text=text + self.VERIFIER_UNAVAILABLE_DISCLAIMER,
                assessment={
                    "hallucination_score": None,
                    "citation_completeness": None,
                    "uncertainty_band": "unknown",
                    "verdict": "verifier_unavailable",
                    "_error": "Verifier LLM call failed",
                },
                forbidden_phrases_rewritten=forbidden_rewrites,
                triage_consistent=True,
            )

        # ── Stage 3.3: Triage consistency check ──
        if triage_level:
            triage_consistent = self._check_triage_consistency(text, triage_level)

        # ── Evaluate result ──
        score = assessment.get("hallucination_score", 1.0)
        verdict = assessment.get("verdict", "rewrite")

        if verdict == "pass" and score <= self._verifier._threshold:
            safe_text = text
            if not triage_consistent:
                safe_text += (
                    "\n\n---\n"
                    "⚠️ **Note:** Our triage assessment suggests a different urgency level "
                    "than the actions described. Please prioritize the more conservative recommendation "
                    "and consult a licensed physician."
                )
            return SafetyGateResult(
                action="pass",
                original_text=assistant_text,
                safe_text=safe_text,
                assessment=assessment,
                forbidden_phrases_rewritten=forbidden_rewrites,
                triage_consistent=triage_consistent,
            )

        elif score >= 0.7:
            return SafetyGateResult(
                action="flag",
                original_text=assistant_text,
                safe_text=self._build_safe_version(text, assessment),
                assessment=assessment,
                forbidden_phrases_rewritten=forbidden_rewrites,
                triage_consistent=triage_consistent,
            )

        # score between 0.3 and 0.7 — rewrite unsupported claims
        return SafetyGateResult(
            action="rewrite",
            original_text=assistant_text,
            safe_text=self._build_safe_version(text, assessment),
            assessment=assessment,
            forbidden_phrases_rewritten=forbidden_rewrites,
            triage_consistent=triage_consistent,
        )

    @staticmethod
    def _build_safe_version(original: str, assessment: dict) -> str:
        """
        يبني نسخة آمنة من الرد — يحذف الجمل غير المدعومة.

        لو الـ verifier رجع unsupported_claims مع suggested_rewrite، بنستبدلها.
        لو رجع من غير rewrite مقترح، بنمسح الجملة.
        لو مفيش unsupported_claims بس score عالي، بنضيف تحذير احتياطي.
        """
        unsupported = assessment.get("unsupported_claims", [])

        if not unsupported:
            return original + PostLLMSafetyGate.UNCERTAINTY_DISCLAIMER

        safe = original

        for claim in unsupported:
            text = claim.get("text", "")
            rewrite = claim.get("suggested_rewrite")

            if text and text in safe:
                if rewrite:
                    safe = safe.replace(text, rewrite)
                else:
                    safe = safe.replace(text, "[claim removed — unsupported by evidence]")

        safe += PostLLMSafetyGate.UNCERTAINTY_DISCLAIMER

        return safe

    # ── Stage 3.2: Forbidden phrase rewriting ──

    @classmethod
    def _rewrite_forbidden_phrases(cls, text: str) -> tuple[str, int]:
        """
        يعيد صياغة العبارات المحظورة (لغة إرشادية صريحة) إلى لغة استشارية آمنة.

        Returns:
            (safe_text, number_of_rewrites)
        """
        count = 0
        safe = text
        for pattern, replacement in cls.FORBIDDEN_PATTERNS:
            before = safe
            safe = re.sub(pattern, replacement, safe, flags=re.IGNORECASE)
            if safe != before:
                count += 1
        return safe, count

    # ── Stage 3.3: Triage consistency check ──

    @classmethod
    def _check_triage_consistency(cls, text: str, triage_level: str) -> bool:
        """
        يتأكد من أن التوصية النهائية في الرد متوافقة مع نتيجة التصنيف.

        المبدأ: إذا triage = emergency، الرد لازم يحوي "go to ER" مش "rest at home".
        إذا triage = routine، الرد مينفعش يقول "call ambulance".

        Returns:
            True if consistent, False if contradictory
        """
        if not triage_level:
            return True

        text_lower = text.lower()
        expected_actions = cls.TRIAGE_ACTION_MAP.get(triage_level, [])

        # Check that at least one expected action keyword exists
        _ = any(action.lower() in text_lower for action in expected_actions)

        # Check for risky mismatches: emergency-level but text says routine actions
        if triage_level == "emergency":
            routine_actions = cls.TRIAGE_ACTION_MAP.get("routine", [])
            has_routine_only = any(
                action.lower() in text_lower for action in routine_actions
            ) and not any(
                action.lower() in text_lower
                for action in cls.TRIAGE_ACTION_MAP.get("emergency", [])
            )
            if has_routine_only:
                return False

        return True

    @staticmethod
    def assessment_to_db(
        assessment: dict,
        message_id: str,
        forbidden_rewrites: int = 0,
        triage_consistent: bool = True,
    ) -> dict:
        """
        يحول نتيجة التدقيق لشكل جاهز للحفظ في جدول safety_assessments.

        Args:
            assessment: dict راجع من verifier.verify()
            message_id: UUID بتاع الرسالة اللي اتقيمت
            forbidden_rewrites: عدد العبارات المحظورة اللي اتعادت صياغتها
            triage_consistent: هل التوصية متطابقة مع التصنيف؟

        Returns:
            dict جاهز لـ INSERT في جدول safety_assessments
        """
        return {
            "message_id": message_id,
            "hallucination_score": assessment.get("hallucination_score"),
            "citation_completeness": assessment.get("citation_completeness"),
            "uncertainty_band": assessment.get("uncertainty_band"),
            "calibration_metadata": assessment.get("claims"),
            "forbidden_phrases_rewritten": forbidden_rewrites,
            "triage_consistent": triage_consistent,
        }
