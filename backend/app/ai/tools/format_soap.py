"""
أداة format_soap — تحويل المحادثة لـ SOAP note (تنسيق سريري)

بياخد conversation_id، يحمّل كل الرسايل، ويحولها لـ S/O/A/P structured note
جاهز للطبيب. بنستخدم LLM عشان الصياغة تكون طبية دقيقة.

دا الـ SOAP note formatter من §8.2.2 في الخطة.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.ai.agent.base import Tool

# ── Input / Output Schemas ──


class SOAPInput(BaseModel):
    """
    conversation_text: نص المحادثة الكامل (كل الرسايل مترقمة)
    language: "ar" أو "en"
    """

    conversation_text: str = Field(
        ..., min_length=1, description="نص المحادثة الكامل مع ترقيم الرسايل"
    )
    language: str = Field(default="en", pattern="^(ar|en)$")


# ── SOAP Formatter ──


class SOAPFormatter:
    """
    بياخد محادثة كاملة ويطلع SOAP note منسق.

    الشغل:
    1. يحمّل prompt من الملف
    2. يبعت المحادثة لـ LLM
    3. يرجع الـ markdown الناتج
    """

    _prompt_path: Path | None = None

    def __init__(self, llm_provider):
        self._llm = llm_provider

        if SOAPFormatter._prompt_path is None:
            SOAPFormatter._prompt_path = (
                Path(__file__).resolve().parent.parent / "prompts" / "soap_en.txt"
            )

    async def format(self, conversation_text: str, language: str = "en") -> dict[str, Any]:
        """
        يحول المحادثة لـ SOAP note.

        Args:
            conversation_text: المحادثة كاملة مع ترقيم الرسايل
            language: لغة الـ note

        Returns:
            dict فيه soap_markdown (النص المنسق) + source_conversation (للرجوع)
        """

        assert SOAPFormatter._prompt_path is not None  # set in __init__
        prompt_template = SOAPFormatter._prompt_path.read_text("utf-8")
        prompt = prompt_template.format(conversation=conversation_text)

        messages = [{"role": "user", "content": prompt}]
        result = await self._llm.generate(
            messages=messages,
            tools=None,
            max_tokens=1024,
            temperature=0.3,
        )

        markdown = result.get("content", "")

        return {
            "soap_markdown": markdown.strip(),
            "format": "soap",
            "sections": ["subjective", "objective", "assessment", "plan"],
        }

    @staticmethod
    def build_conversation_text(messages: list[dict]) -> str:
        """
        يبني نص المحادثة من قائمة الرسايل.

        كل رسالة بتبقى:
        [msg:1] (user): السلام عليكم
        [msg:2] (assistant): وعليكم السلام...

        دا بيساعد الـ LLM يرجع للمصدر في الـ SOAP note.
        """
        lines = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                lines.append(f"[msg:{i}] ({role}): {content}")
        return "\n\n".join(lines)


# ── Tool ──


class FormatSOAPTool(Tool):
    """أداة تنسيق SOAP — بتحول المحادثة لتقرير طبي منظم."""

    def __init__(self, llm_provider):
        self._formatter = SOAPFormatter(llm_provider)

    @property
    def name(self) -> str:
        return "format_soap_note"

    @property
    def description(self) -> str:
        return (
            "Format the entire conversation into a structured SOAP "
            "(Subjective, Objective, Assessment, Plan) clinical note. "
            "Useful for generating a doctor-ready summary of the encounter."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return SOAPInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, SOAPInput):
            raise TypeError(f"Expected SOAPInput, got {type(input_data)}")

        return await self._formatter.format(
            conversation_text=input_data.conversation_text,
            language=input_data.language,
        )
