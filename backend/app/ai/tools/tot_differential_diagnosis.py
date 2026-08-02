"""
أداة tot_differential_diagnosis — تشخيص تفريقي متعدد الفروع (Tree-of-Thought)

لما الأعراض تكون ambiguous (مش واضحة) والـ triage urgent، الأداة دي بتولّد
3 فروع تشخيصية (hypotheses)، ترجع لكل فرع supporting evidence من الـ RAG،
وتختار أفضل 2 فيهم للعرض على المريض.

دا الـ ToT mode من §8.8.2 في الخطة.
"""

import json
import re
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

MAX_TOT_BRANCHES = 3  # الحد الأقصى للفروع
MAX_TOT_DEPTH = 2  # أقصى عمق للتفكير


# ── Input / Output Schemas ──


# class ToTInput(BaseModel):
#     """
#     مدخلات أداة التشخيص التفريقي.

#     symptoms: الأعراض اللي قالها المريض (نص وصفي)
#     history: التاريخ المرضي — عمر، أمراض مزمنة، أدوية، حساسية
#     sources: المصادر الطبية من RAG
#     language: "ar" أو "en"
#     """

#     symptoms: str = Field(..., min_length=1, description="وصف الأعراض من المريض")
#     history: str = Field(default="", description="العمر، الأمراض المزمنة، الأدوية")
#     sources: list[dict[str, str]] = Field(
#         default_factory=list,
#         description="المصادر الطبية المسترجعة من RAG",
#     )
#     language: str = Field(default="en", pattern="^(ar|en)$")


# ----------------------------------
class ToTInput(BaseModel):
    """
    مدخلات أداة التشخيص التفريقي.
    """

    symptoms: Any = Field(default="", description="وصف الأعراض من المريض")
    history: Any = Field(default="", description="العمر، الأمراض المزمنة، الأدوية")
    sources: Any = Field(
        default=[],
        description="المصادر الطبية المسترجعة من RAG",
    )
    language: Any = Field(default="ar")

    # 🟢 فلتر الأعراض والتاريخ المرضي (لو الموديل بعتهم List هنحولهم String)
    @field_validator("symptoms", "history", mode="before")
    @classmethod
    def force_string(cls, v):
        if v is None or str(v).lower() == "null":
            return ""
        if isinstance(v, list):
            return ", ".join([str(item) for item in v])
        return str(v)

    # 🟢 فلتر المصادر (لو الموديل بعتها نص، هنغلفها في قاموس عشان الكود بتاعك ميضربش)
    @field_validator("sources", mode="before")
    @classmethod
    def force_list_of_dicts(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return []

        # لو الموديل بعت المصادر كنص عادي
        if isinstance(v, str):
            return [{"source": "LLM_provided", "content": v}]

        # لو بعتها قائمة، نتأكد إن جواها قواميس مش نصوص
        if isinstance(v, list):
            clean_list = []
            for item in v:
                if isinstance(item, dict):
                    clean_list.append(item)
                elif isinstance(item, str):
                    clean_list.append({"source": "LLM_provided", "content": item})
            return clean_list

        return []

    # 🟢 فلتر اللغة
    @field_validator("language", mode="before")
    @classmethod
    def force_lang(cls, v):
        if isinstance(v, str) and v.lower() in ["ar", "en"]:
            return v.lower()
        return "ar"


# ── ToT Engine ──


class ToTDifferentialEngine:
    """
    محرك التشخيص التفريقي — بيولّد فروع تشخيصية ويسجلها.

    بيشتغل على 3 مراحل:
    1. Branch generation — يطلب من LLM يطلع 3 hypotheses
    2. Branch scoring — يرجع لكل فرع المصادر اللي بتدعمه
    3. Pruning — يختار أفضل 2 فروع ويعرضهم
    """

    _PROMPT_PATHS: ClassVar[dict[str, Path]] = {}

    def __init__(self, llm_provider):
        """
        llm_provider: أي instance من LLMProvider
        """
        self._llm = llm_provider

        # Cache prompt paths for both languages — picked at runtime per call.
        if not ToTDifferentialEngine._PROMPT_PATHS:
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
            ToTDifferentialEngine._PROMPT_PATHS = {
                "ar": prompts_dir / "tot_differential_ar.txt",
                "en": prompts_dir / "tot_differential_en.txt",
            }

    async def generate_branches(
        self,
        symptoms: str,
        history: str,
        sources: list[dict],
        language: str = "ar",
    ) -> dict[str, Any]:
        """
        يولّد الفروع التشخيصية باستخدام LLM.

        1. يبني الـ prompt بالمدخلات
        2. يبعت لـ LLM (non-streaming)
        3. يفسر الـ JSON الراجع
        4. يختار أفضل 2 (pruning)

        ``language`` selects the prompt (ar/en) so the LLM emits hypothesis
        names + reasoning + evidence in the user's language. Defaults to AR
        because Arabic is the platform's default locale.
        """

        # 1. نبني الـ prompt — بناءً على لغة المريض
        prompt_path = (
            ToTDifferentialEngine._PROMPT_PATHS.get(language)
            or (ToTDifferentialEngine._PROMPT_PATHS["en"])
        )
        prompt_template = prompt_path.read_text("utf-8")
        sources_text = self._format_sources(sources)

        # prompt = prompt_template.format(
        #     symptoms=symptoms,
        #     history=history or "No significant history reported",
        #     sources=sources_text
        #     or "(No medical sources available — use general clinical knowledge)",
        # )
        # استخدمنا replace عشان بايثون متتلخبطش بين متغيراتنا وأقواس الـ JSON
        prompt = (
            prompt_template.replace("{symptoms}", str(symptoms))
            .replace("{history}", str(history) or "No significant history reported")
            .replace(
                "{sources}",
                str(sources_text)
                or "(No medical sources available — use general clinical knowledge)",
            )
        )

        # 2. نبعت لـ LLM
        messages = [{"role": "user", "content": prompt}]
        result = await self._llm.generate(
            messages=messages,
            tools=None,
            max_tokens=1024,
            temperature=0.4,  # شوية إبداع عشان الفروع تكون متنوعة
        )

        raw_content = result.get("content", "")

        # 3. نفسر الـ JSON
        tot_result = self._parse_json(raw_content)
        branches = tot_result.get("branches", [])

        # 4. Pruning — نخلي أفضل 2 (أو 3 لو قليلين)
        if len(branches) > 2:
            # نرتبهم حسب probability (الأعلى أولاً)
            branches.sort(key=lambda b: b.get("probability", 0), reverse=True)
            branches = branches[:2]

        return {
            "branches": branches,
            "mode": "tree_of_thought",
            "total_branches_generated": len(branches),
        }

    @staticmethod
    def _format_sources(sources: list[dict]) -> str:
        """ينسق المصادر لنص مقروء للـ LLM."""
        if not sources:
            return ""

        lines = []
        for i, src in enumerate(sources):
            title = src.get("title", src.get("source", f"Source {i}"))
            content = src.get("content", src.get("content_excerpt", ""))
            if len(content) > 400:
                content = content[:400] + "..."
            lines.append(f"[{i}] {title}")
            lines.append(f"    {content}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """يستخرج JSON من رد الـ LLM (مع تعامل مع markdown fences)."""
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {"branches": [], "_raw": raw[:200], "_parse_error": True}


# ── Tool ──


class ToTDifferentialDiagnosisTool(Tool):
    """
    الأداة المسجلة في ToolRegistry — تشخيص تفريقي متعدد الفروع.

    الـ Agent بيستخدمها لما يكتشف إن الأعراض ambiguous ومحتاجة تحليل أعمق.
    """

    def __init__(self, llm_provider):
        self._engine = ToTDifferentialEngine(llm_provider)

    @property
    def name(self) -> str:
        return "tot_differential_diagnosis"

    @property
    def description(self) -> str:
        return (
            "Generate multiple diagnostic hypotheses (Tree-of-Thought branching) for "
            "ambiguous symptom presentations. Returns 2-3 ranked branches with "
            "probability scores, supporting evidence, and recommended actions. "
            "Use when symptoms are unclear and multiple distinct conditions could explain them."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return ToTInput

    # async def run(self, input_data: BaseModel) -> dict[str, Any]:
    #     if not isinstance(input_data, ToTInput):
    #         raise TypeError(f"Expected ToTInput, got {type(input_data)}")

    #     return await self._engine.generate_branches(
    #         symptoms=input_data.symptoms,
    #         history=input_data.history,
    #         sources=input_data.sources,
    #     )
    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, ToTInput):
            raise TypeError(f"Expected ToTInput, got {type(input_data)}")

        try:
            return await self._engine.generate_branches(
                symptoms=input_data.symptoms,
                history=input_data.history,
                sources=input_data.sources,
                language=input_data.language,
            )
        except Exception as e:
            import structlog

            structlog.get_logger(__name__).warning("tot_engine_error", error=str(e))
            return {"error": f"Failed to generate branches: {e!s}"}
