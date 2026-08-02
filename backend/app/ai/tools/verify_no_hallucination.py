"""
أداة verify_no_hallucination — مدقق الهلاوس بعد توليد الرد

بعد ما الـ Agent يطلع رد، الأداة دي بتبعت الرد + المصادر الطبية
لـ LLM مدقق (يفضل موديل صغير 3B) عشان يقارن كل claim بمصدره.

النتيجة:
- hallucination_score (0 = مفيش هلاوس، 1 = كله هلاوس)
- قائمة بكل claim وتقييمه (supported/unsupported + confidence)
- claims غير مدعومة مع اقتراح لإعادة الصياغة

دا الـ Stage 3 من safety pipeline بتاعنا (§8.3).
"""

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# ── Input / Output Schemas ──


# class VerifierInput(BaseModel):
#     """
#     المدخلات اللي الـ verifier بيستقبلها.

#     assistant_message: النص الكامل لرد الـ Agent على المريض
#     sources: قائمة المصادر اللي رجعها الـ RAG — كل مصدر فيه title و content
#     """

#     assistant_message: str = Field(
#         ...,
#         min_length=1,
#         description="النص الكامل اللي الـ Agent رجعه للمريض",
#     )


#     sources: list[dict[str, str]] = Field(
#         default_factory=list,
#         description="المصادر الطبية اللي استخدمها الـ Agent — كل عنصر: {title, content}",
#     )
# -------------------------------
class VerifierInput(BaseModel):
    """
    المدخلات اللي الـ verifier بيستقبلها.
    """

    assistant_message: Any = Field(
        default="",
        description="النص الكامل اللي الـ Agent رجعه للمريض",
    )

    sources: Any = Field(
        default=[],
        description="المصادر الطبية اللي استخدمها الـ Agent — كل عنصر: {title, content}",
    )

    # 🟢 فلتر الرسالة (لو بعتها List نلمها في String)
    @field_validator("assistant_message", mode="before")
    @classmethod
    def force_string(cls, v):
        if v is None or str(v).lower() == "null":
            return ""
        if isinstance(v, list):
            return " ".join([str(item) for item in v])
        return str(v)

    # 🟢 فلتر المصادر (يحول أي عك يبعته الموديل لـ List of Dicts سليم)
    @field_validator("sources", mode="before")
    @classmethod
    def force_list_of_dicts(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return []

        # لو بعتها نص، نغلفها في قاموس
        if isinstance(v, str):
            return [{"source": "Agent_Memory", "content": v}]

        # لو بعتها قائمة، ننضفها ونتأكد إن جواها قواميس
        if isinstance(v, list):
            clean_list = []
            for item in v:
                if isinstance(item, dict):
                    clean_list.append(item)
                elif isinstance(item, str):
                    clean_list.append({"source": "Agent_Memory", "content": item})
            return clean_list

        return []


# ── Verifier Logic ──


class HallucinationVerifier:
    """
    محرك كشف الهلاوس — بياخد رد الـ Agent والمصادر، ويشغل LLM صغير عشان يراجع.

    المبدأ: الـ LLM الصغير دا (verifier) مش بيولد محتوى جديد — بيقارن بس.
    كل جملة طبية في الرد لازم يكون ليها مصدر في الـ sources.
    لو مفيش مصدر → الجملة مش مدعومة (unsupported) ← = هلوسة.

    الـ threshold الافتراضي 0.3 — لو درجة الهلاوس أعلى من كدا، الرد بيتعدل أو بيترفض.
    """

    # المسار لملف الـ prompt بتاعنا
    _prompt_path: Path | None = None

    def __init__(self, llm_provider, threshold: float = 0.3):
        """
        # بينشئ مدقق الهلاوس.
        #
        # llm_provider: اي instance من LLMProvider — بنستخدم generate() مش streaming عشان السرعة
        # threshold: الحد الأقصى لدرجة الهلاوس قبل ما نرفض الرد
        """
        self._llm = llm_provider
        self._threshold = threshold
        # بنحمل الـ prompt مرة واحدة (cached)
        if HallucinationVerifier._prompt_path is None:
            HallucinationVerifier._prompt_path = (
                Path(__file__).resolve().parent.parent / "prompts" / "verifier_en.txt"
            )

    # ── تنسيق المصادر ──

    @staticmethod
    def _format_sources(sources: list[dict]) -> str:
        """
        بيحول قائمة المصادر لنص مقروء للـ LLM.

        المصدر بيتحول لشكل:
        [0] عنوان المصدر
            محتوى المصدر (أول 500 حرف)...
        """
        if not sources:
            return "(No sources provided — the assistant had no evidence to draw from)"

        lines = []
        for i, src in enumerate(sources):
            title = src.get("title", src.get("source", f"Source {i}"))
            content = src.get("content", src.get("content_excerpt", ""))
            # لو المحتوى طويل جداً، نقطع منه (الـ LLM الصغير ليه window صغير)
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"[{i}] {title}")
            lines.append(f"    {content}")
            lines.append("")

        return "\n".join(lines)

    # ── التحليل ──

    async def verify(self, assistant_message: str, sources: list[dict]) -> dict[str, Any]:
        """
        # يشغل مدقق الهلاوس على رد الـ Agent.
        #
        # 1. بيجهز الـ prompt بدمج المصادر + الرد
        # 2. بيبعت لـ LLM (non-streaming — عايزين الرد كامل مرة واحدة)
        # 3. بيفسر الـ JSON الراجع
        # 4. لو الـ JSON مش مظبوط، بيعمل fallback آمن
        """
        # لو مفيش مصادر من الأساس — كله unsupported
        if not sources:
            return {
                "hallucination_score": 1.0,
                "citation_completeness": 0.0,
                "claims": [],
                "unsupported_claims": [
                    {
                        "text": assistant_message,
                        "suggested_rewrite": None,
                        "severity": "high",
                    }
                ],
                "verdict": "rewrite",  # rewrite / pass / flag
                "_note": "No sources available — cannot verify any claims",
            }

        # 1. نحمّل الـ prompt ونستبدل المتغيرات
        prompt_template = HallucinationVerifier._prompt_path.read_text(encoding="utf-8")
        sources_text = self._format_sources(sources)

        prompt = prompt_template.format(
            sources=sources_text,
            response=assistant_message,
        )

        # 2. نبعت لـ LLM (non-streaming — عشان نستقبل JSON كامل)
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        result = await self._llm.generate(
            messages=messages,
            tools=None,  # مش محتاجين أدوات هنا
            max_tokens=1024,
            temperature=0.0,  # temperature=0 يعني deterministic — مفيش عشوائية في التدقيق
        )

        raw_content = result.get("content", "")

        # 3. نفسر الـ JSON اللي رجع
        verification = self._parse_verifier_json(raw_content)

        # 4. نضيف verdict (القرار النهائي)
        score = verification.get("hallucination_score", 0.0)
        verification["verdict"] = "rewrite" if score > self._threshold else "pass"

        return verification

    # ── مساعد: تفسير JSON ──

    @staticmethod
    def _parse_verifier_json(raw: str) -> dict[str, Any]:
        """
        بيستخرج JSON من رد الـ LLM. LLMs أحياناً بتحط markdown fences:
        ```json
        {...}
        ```
        أو علامات تنصيص. الوظيفة دي بتتعامل مع كل الحالات.
        """
        # 1. نحاول تفسير النص كله مباشرة
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        # 2. نحاول نستخرج JSON من جوه markdown fence
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 3. فشل التفسير — نعتبر الرد كله مش مدعوم (fail-safe)
        return {
            "hallucination_score": 1.0,
            "citation_completeness": 0.0,
            "claims": [],
            "unsupported_claims": [
                {
                    "text": "COULD NOT PARSE VERIFIER RESPONSE",
                    "suggested_rewrite": None,
                    "severity": "high",
                }
            ],
            "_raw_response": raw[:500],  # نحتفظ بالرد للتصحيح
            "_parse_error": True,
        }


# ── Tool ──


class VerifyNoHallucinationTool(Tool):
    """
    الاداة اللي بتسجل في ToolRegistry — الـ Agent يقدر يستخدمها لو محتاج.

    لكن في الواقع، الأداة دي مش هيتصل بيها الـ Agent من جوه الـ loop.
    هنستخدمها من بره الـ loop — في الـ post-LLM gate (الخطوة الجاية).

    السبب: التدقيق على الهلاوس مش جزء من تفكير الـ Agent — دا تفتيش خارجي
    بيحصل بعد ما الـ Agent يخلص رده. فالأداة موجودة كـ Tool عشان:
    1. تقدر تختبرها بشكل مستقل
    2. تقدر تسجلها في الـ registry لو احتجت
    3. الكود منظم في مكانه الصح تحت tools/
    """

    def __init__(self, llm_provider, threshold: float = 0.3):
        self._verifier = HallucinationVerifier(llm_provider, threshold)

    @property
    def name(self) -> str:
        return "verify_no_hallucination"

    @property
    def description(self) -> str:
        return (
            "Verify that every clinical claim in the assistant's response is supported "
            "by at least one retrieved medical source. Returns a hallucination score "
            "(0 = fully grounded, 1 = fully hallucinated) and per-claim confidence. "
            "Use this when you need to double-check your own response before sending."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return VerifierInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        """
        # يشغل أداة كشف الهلاوس.
        #
        # بنستدعي verify() اللي بدورها بتشغل LLM صغير للتدقيق.
        # النتيجة بنرجعها كـ dict عشان الـ Agent أو الـ safety gate يستخدمها.
        """
        if not isinstance(input_data, VerifierInput):
            raise TypeError(f"Expected VerifierInput, got {type(input_data)}")

        return await self._verifier.verify(
            assistant_message=input_data.assistant_message,
            sources=input_data.sources,
        )
