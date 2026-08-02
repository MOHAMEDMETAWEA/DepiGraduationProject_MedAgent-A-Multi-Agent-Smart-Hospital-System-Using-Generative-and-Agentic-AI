"""
أداة calibrate_uncertainty — معايرة درجة الثقة لكل جملة طبية

بعد ما الـ verifier (T2.5.01) يحلل الرد، الأداة دي بتقسم الرد لجمل،
وتربط كل جملة بنتيجة التدقيق بتاعها، وتضيف band (high/medium/low).

الهدف: المريض يشوف badge جنب كل claim: "⚠️ ثقة منخفضة" أو "✅ مصادر قوية".

الأداة مش بتستخدم LLM — مجرد post-processor سريع.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# ── Input / Output Schemas ──


# class CalibrateInput(BaseModel):
#     """
#     المدخلات: الرد الكامل + نتيجة التدقيق من T2.5.01 (اختياري).

#     assistant_message: نص الرد اللي وصل للمريض
#     assessment: نتيجة verify_no_hallucination (لو موجودة) — اختياري
#     sources: المصادر الطبية — اختياري، بنستخدمها لو مفيش assessment
#     """


#     assistant_message: str = Field(..., min_length=1)
#     assessment: dict[str, Any] | None = Field(
#         default=None,
#         description="نتيجة التدقيق من verify_no_hallucination — فيها claims و unsupported_claims",
#     )
#     sources: list[dict[str, str]] = Field(
#         default_factory=list,
#         description="المصادر الطبية (لحساب الثقة يدوياً لو مفيش assessment)",
#     )
# ---------------
class CalibrateInput(BaseModel):
    """
    المدخلات: الرد الكامل + نتيجة التدقيق من T2.5.01 (اختياري).
    """

    assistant_message: Any = Field(default="", description="نص الرد اللي وصل للمريض")
    assessment: Any = Field(
        default=None,
        description="نتيجة التدقيق من verify_no_hallucination — فيها claims و unsupported_claims",
    )
    sources: Any = Field(
        default=[],
        description="المصادر الطبية (لحساب الثقة يدوياً لو مفيش assessment)",
    )

    # 🟢 فلتر النص (عشان لو الموديل بعت list بدل string)
    @field_validator("assistant_message", mode="before")
    @classmethod
    def force_string(cls, v):
        if v is None or str(v).lower() == "null":
            return ""
        if isinstance(v, list):
            return " ".join([str(item) for item in v])
        return str(v)

    # 🟢 فلتر الـ Assessment (عشان نضمن إنه Dict سليم أو None)
    @field_validator("assessment", mode="before")
    @classmethod
    def force_dict(cls, v):
        if v is None or str(v).lower() == "null" or v == "":
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"claims": [], "unsupported_claims": [], "fallback_raw": v}
        return None

    # 🟢 فلتر المصادر (عشان نحول أي حاجة لـ List of Dicts)
    @field_validator("sources", mode="before")
    @classmethod
    def force_list_of_dicts(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return []

        if isinstance(v, str):
            return [{"source": "Agent_Memory", "content": v}]

        if isinstance(v, list):
            clean_list = []
            for item in v:
                if isinstance(item, dict):
                    clean_list.append(item)
                elif isinstance(item, str):
                    clean_list.append({"source": "Agent_Memory", "content": item})
            return clean_list

        return []


# ── Calibrator Logic ──


class UncertaintyCalibrator:
    """
    بياخد رد الـ Agent وبيطلع كل جملة مع درجة ثقتها.

    منطق الشغل:
    1. يقسم الرد لجمل (بالنقطة أو السطر الجديد)
    2. يوصّل كل جملة بـ claim من نتيجة الـ verifier (لو موجودة)
    3. يحسب band: high/medium/low
    4. يرجع قائمة claims جاهزة للـ Frontend
    """

    @staticmethod
    def calibrate(
        assistant_message: str,
        assessment: dict | None = None,
        sources: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        يحلل الرد ويربط كل جملة بدرجة ثقة.

        لو في assessment (من T2.5.01): بنستخدم بياناته مباشرة.
        لو مفيش: بنعمل تحليل بسيط بدون LLM.
        """
        # نقسم الرد لجمل
        sentences = UncertaintyCalibrator._split_sentences(assistant_message)

        # لو في assessment، نطابق الجمل مع claims المدققة
        if assessment:
            return UncertaintyCalibrator._calibrate_from_assessment(sentences, assessment)

        # مفيش assessment — نرجع كل الجمل بثقة unknown
        return UncertaintyCalibrator._calibrate_fallback(sentences, sources or [])

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        يقسم النص لجمل.

        بنستخدم النقطة، علامة الاستفهام، التعجب، والسطر الجديد كفواصل.
        بنحافظ على الجمل الفاضية بره.
        """
        # regex: نقطة أو ? أو ! أو سطر جديد — متبوعين بمسافة أو نهاية النص
        raw = re.split(r"(?<=[.?!\n])\s+", text)
        return [s.strip() for s in raw if s.strip()]

    @staticmethod
    def _calibrate_from_assessment(sentences: list[str], assessment: dict) -> dict[str, Any]:
        """
        يطابق كل جملة مع claim من نتيجة الـ verifier.

        المنطق: بناخد الـ claims اللي رجعها الـ verifier (مدعومة وغير مدعومة)
        ونحاول نلاقي كل جملة فيهم. لو لقيناها، ناخد درجة ثقتها.
        لو ملقتناهاش، نحطها unknown (مش جملة طبية مثلاً).
        """
        all_claims = assessment.get("claims", [])
        unsupported = assessment.get("unsupported_claims", [])

        # ندمج كل الـ claims (المدعومة + غير المدعومة) في قاموس للبحث السريع
        claim_map: dict[str, dict] = {}

        # الـ claims المدعومة — كل واحدة فيها text, confidence, band
        for c in all_claims:
            claim_map[c.get("text", "")] = {
                "confidence": c.get("confidence", 0.5),
                "band": c.get("band", "medium"),
                "supported": c.get("supported", True),
            }

        # الـ claims غير المدعومة — severity بدل confidence
        for uc in unsupported:
            severity = uc.get("severity", "medium")
            # severity "high" → band "low", severity "medium" → band "low"
            claim_map[uc.get("text", "")] = {
                "confidence": 0.1,
                "band": "low",
                "supported": False,
                "severity": severity,
            }

        result_claims = []
        for sentence in sentences:
            # نحاول نلاقي الجملة في الـ claims (تطابق تام أو جزئي)
            matched = UncertaintyCalibrator._find_match(sentence, claim_map)

            if matched:
                result_claims.append(
                    {
                        "text": sentence,
                        "confidence": matched.get("confidence"),
                        "band": matched.get("band", "medium"),
                        "supported": matched.get("supported", False),
                    }
                )
            else:
                # الجملة مش جملة طبية (تحية، disclaimer، إلخ)
                result_claims.append(
                    {
                        "text": sentence,
                        "confidence": None,
                        "band": "none",  # مش محتاجة badge
                        "supported": None,
                    }
                )

        # نحسب uncertainty_band العام للرد كله
        bands = [c["band"] for c in result_claims if c["band"] != "none"]
        overall = UncertaintyCalibrator._overall_band(bands)

        return {
            "claims": result_claims,
            "uncertainty_band": overall,
        }

    @staticmethod
    def _calibrate_fallback(sentences: list[str], sources: list[dict]) -> dict[str, Any]:
        """
        مفيش assessment من الـ verifier — بنعمل تحليل بسيط بدون LLM.

        بنحسب ثقة كل جملة بناءً على وجود كلماتها في المصادر.
        دا مش دقيق 100% لكنه احتياطي.
        """
        claims = []
        for sentence in sentences:
            if not UncertaintyCalibrator._is_clinical(sentence):
                claims.append(
                    {
                        "text": sentence,
                        "confidence": None,
                        "band": "none",
                        "supported": None,
                    }
                )
                continue

            # نشوف كام مصدر بيحتوي على كلمات الجملة
            match_count = 0
            sentence_lower = sentence.lower()
            for src in sources:
                content = (src.get("content", "") + " " + src.get("title", "")).lower()
                # overlap بسيط: لو نص الكلمات موجودة في المصدر
                words = [w for w in sentence_lower.split() if len(w) > 3]
                if words and sum(1 for w in words if w in content) / len(words) > 0.3:
                    match_count += 1

            if match_count >= 2:
                band, confidence = "high", 0.9
            elif match_count == 1:
                band, confidence = "medium", 0.7
            else:
                band, confidence = "low", 0.3

            claims.append(
                {
                    "text": sentence,
                    "confidence": confidence,
                    "band": band,
                    "supported": match_count > 0,
                }
            )

        return {
            "claims": claims,
            "uncertainty_band": UncertaintyCalibrator._overall_band(
                [c["band"] for c in claims if c["band"] != "none"]
            ),
        }

    @staticmethod
    def _find_match(sentence: str, claim_map: dict[str, dict]) -> dict | None:
        """
        يدور على الجملة في قاموس الـ claims.

        بيجرب:
        1. تطابق تام
        2. الجملة جوه claim
        3. claim جوه الجملة
        """
        # 1. تطابق تام
        if sentence in claim_map:
            return claim_map[sentence]

        # 2. الجملة جزء من claim (الـ claim أطول)
        for claim_text, data in claim_map.items():
            if sentence in claim_text:
                return data

        # 3. claim جزء من الجملة (الـ claim أقصر)
        for claim_text, data in claim_map.items():
            if len(claim_text) > 10 and claim_text in sentence:
                return data

        return None

    @staticmethod
    def _is_clinical(sentence: str) -> bool:
        """
        بيحدد إذا كانت الجملة طبية (محتاجة badge) ولا مجرد كلام عادي.
        """
        clinical_keywords = [
            "symptom",
            "pain",
            "diagnosis",
            "treatment",
            "disease",
            "condition",
            "medication",
            "drug",
            "dose",
            "therapy",
            "infection",
            "chronic",
            "acute",
            "syndrome",
            "blood",
            "heart",
            "lung",
            "liver",
            "kidney",
            "cancer",
            "diabetes",
            "pressure",
            "allergy",
            "risk",
            "emergency",
            "consult",
            "doctor",
            "physician",
            "hospital",
        ]
        sentence_lower = sentence.lower()
        return any(kw in sentence_lower for kw in clinical_keywords)

    @staticmethod
    def _overall_band(bands: list[str]) -> str:
        """يحسب الـ band العام للرد كله."""
        if not bands:
            return "unknown"
        if "low" in bands:
            return "low"
        if "medium" in bands:
            return "medium"
        return "high"


# ── Tool ──


class CalibrateUncertaintyTool(Tool):
    """
    الأداة المسجلة في ToolRegistry — بتعاير درجة الثقة لكل جملة.

    زي verify_no_hallucination، الأداة دي مش بيستخدمها الـ Agent من جوه.
    بنستخدمها من الـ post-LLM gate أو من الـ chat endpoint بعد التدقيق.
    """

    @property
    def name(self) -> str:
        return "calibrate_uncertainty"

    @property
    def description(self) -> str:
        return (
            "Analyze each sentence in the assistant's response and assign a confidence "
            "band (high/medium/low/none). Uses verification results if available, "
            "otherwise falls back to lightweight source matching."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return CalibrateInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, CalibrateInput):
            raise TypeError(f"Expected CalibrateInput, got {type(input_data)}")

        return UncertaintyCalibrator.calibrate(
            assistant_message=input_data.assistant_message,
            assessment=input_data.assessment,
            sources=input_data.sources,
        )
