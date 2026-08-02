"""Tool: summarize_for_doctor — generates structured SOAP note from conversation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# ── Schema ──


class SummaryInput(BaseModel):
    """Input schema for doctor summary generation."""

    conversation_id: str = Field(
        # ...,
        # min_length=1,
        # description="Conversation UUID to load messages from",
        default="",  # 🟢 شيلنا min_length=1 خالص
        description="Conversation UUID. Leave empty, the system will inject it automatically.",
    )
    chat_history: Any = Field(
        default="",
        description="IMPORTANT: If conversation_id is empty, provide a detailed summary of the patient's symptoms and history here.",
    )
    language: str = Field(
        default="en",
        pattern="^(ar|en)$",
    )
    # triage_level: str | None = None
    # triage_score: int | None = None
    # red_flags: list[str] | None = None
    # ---------------------------
    triage_level: str = Field(
        default="",
        description="Detected triage level (e.g., 'routine', 'urgent', 'emergency'). Pass empty string if unknown.",
    )
    triage_score: str = Field(
        default="",
        description="Triage score out of 100 as a string (e.g., '85'). Pass empty string if unknown.",
    )
    red_flags: str = Field(
        default="",
        description="Comma-separated list of red flags if any. Pass empty string if none.",
    )

    # 🟢 فلتر الحماية اللي اتعودنا عليه
    @field_validator(
        "conversation_id",
        "chat_history",
        "language",
        "triage_level",
        "triage_score",
        "red_flags",
        mode="before",
    )
    @classmethod
    def force_string(cls, v):
        if v is None or str(v).lower() == "null":
            return ""
        return str(v)


# ── Tool ──


class SummarizeForDoctorTool(Tool):
    """
    Generates a structured SOAP-format summary from a patient conversation.

    Uses prompt templates (doctor_summary_en.txt / doctor_summary_ar.txt)
    and passes the formatted prompt to the LLM provider.
    """

    def __init__(self, llm=None):
        self._llm = llm
        self._prompts: dict[str, str] = {}

    def set_llm(self, llm):
        """Set the LLM provider (called by the agent after initialization)."""
        self._llm = llm

    def _load_prompt(self, language: str) -> str:
        """Load the prompt template for the given language (cached)."""
        if language not in self._prompts:
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
            filename = f"doctor_summary_{language}.txt"
            with open(prompts_dir / filename, encoding="utf-8") as f:
                self._prompts[language] = f.read()
        return self._prompts[language]

    # ── Tool interface ──

    @property
    def name(self) -> str:
        return "summarize_for_doctor"

    @property
    def description(self) -> str:
        return (
            "Generate a structured SOAP-format clinical summary from a conversation "
            "transcript. Includes chief complaint, history, symptoms, risk factors, "
            "red flags, triage assessment, and recommended next steps. Use at the "
            "end of a triage session to prepare the doctor handoff."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return SummaryInput

    # async def run(self, input_data: BaseModel) -> dict[str, Any]:
    #     """Load messages from conversation and generate summary."""
    #     if not isinstance(input_data, SummaryInput):
    #         raise TypeError(f"Expected SummaryInput, got {type(input_data)}")

    #     # Load conversation messages
    #     import uuid

    #     from sqlalchemy import select

    #     from app.core.database import get_session
    #     from app.models.messages import Message

    #     async with get_session() as session:
    #         result = await session.execute(
    #             select(Message)
    #             .where(Message.conversation_id == uuid.UUID(input_data.conversation_id))
    #             .order_by(Message.created_at.asc())
    #         )
    #         messages = list(result.scalars().all())
    #         conversation_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        """Load messages from conversation and generate summary."""
        if not isinstance(input_data, SummaryInput):
            raise TypeError(f"Expected SummaryInput, got {type(input_data)}")

        conversation_text = ""

        # 1. لو الزرار هو اللي باعت (فيها ID حقيقي)، هنجيب من الداتابيز بأمان
        if input_data.conversation_id and len(str(input_data.conversation_id)) > 10:
            import uuid

            from sqlalchemy import select

            from app.core.database import get_session
            from app.models.messages import Message

            try:
                async with get_session() as session:
                    result = await session.execute(
                        select(Message)
                        .where(
                            Message.conversation_id == uuid.UUID(str(input_data.conversation_id))
                        )
                        .order_by(Message.created_at.asc())
                    )
                    messages = list(result.scalars().all())
                    conversation_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
            except Exception as e:
                print(f"UUID or DB Error: {e}")  # عشان لو حصل مشكلة السيرفر ميكراشش

        # 2. لو الموديل هو اللي مستدعيها من الشات (مفيش ID)، نعتمد على كلامه
        if not conversation_text:
            if input_data.chat_history:
                conversation_text = input_data.chat_history
            else:
                # لو الموديل استعبط ومبعتش حاجة خالص، نرجعه يكتب هو التلخيص
                return {
                    "error": "Missing conversation_id and chat_history. Please generate the summary yourself directly in the chat."
                }

        # Build context for the prompt
        extra_context = []
        # 👇👇👇 (كمل باقي الكود بتاعك من أول هنا زي ما هو بدون تعديل) 👇👇👇
        if input_data.triage_level:
            extra_context.append(f"Triage level: {input_data.triage_level}")

        # Build context for the prompt
        extra_context = []
        if input_data.triage_level:
            extra_context.append(f"Triage level: {input_data.triage_level}")
        if input_data.triage_score is not None:
            extra_context.append(f"Triage score: {input_data.triage_score}")
        if input_data.red_flags:
            extra_context.append(f"Red flags: {', '.join(input_data.red_flags)}")

        context_str = "\n".join(extra_context)
        full_text = conversation_text
        if context_str:
            full_text = f"{context_str}\n\n{full_text}"

        if self._llm:
            prompt_template = self._load_prompt(input_data.language)
            prompt = prompt_template.format(conversation=full_text)
            result = await self._llm.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.2,
            )
            summary = result.get("content", "")
        else:
            lines = [
                "## Chief Complaint",
                "(Generated from patient conversation)",
                "",
                "## Symptoms Summary",
                f"Based on transcript: {conversation_text[:200]}...",
                "",
            ]
            if input_data.triage_level:
                lines.append("## AI Triage")
                lines.append(f"Level: {input_data.triage_level}, Score: {input_data.triage_score}")
            lines.append("")
            lines.append("## Recommended Next Steps")
            lines.append("(Review full transcript for clinical decision-making)")
            summary = "\n".join(lines)

        return {
            "summary_markdown": summary,
            "language": input_data.language,
        }
