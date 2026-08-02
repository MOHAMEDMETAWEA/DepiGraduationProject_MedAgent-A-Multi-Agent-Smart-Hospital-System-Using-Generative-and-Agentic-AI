"""Tool: screen_mental_health — PHQ-9 / GAD-7 screening with suicidality escalation."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# class MentalHealthInput(BaseModel):
#     """Input schema for mental health screening."""


#     responses: list[int] = Field(
#         ...,
#         min_length=9,
#         description="Patient responses to screening questions (0-3 scale). Must match question count.",
#     )
#     screening_type: str = Field(
#         default="phq9",
#         pattern="^(phq9|gad7)$",
#         description="Type of screening: 'phq9' or 'gad7'",
#     )
#     language: str = Field(
#         default="en",
#         pattern="^(ar|en)$",
#         description="Response language",
#     )
# --------------------------------
class MentalHealthInput(BaseModel):
    """Input schema for mental health screening."""

    responses: Any = Field(
        default=[],
        description="Patient responses to screening questions (0-3 scale). Must match question count.",
    )
    screening_type: Any = Field(
        default="phq9",
        description="Type of screening: 'phq9' or 'gad7'",
    )
    language: Any = Field(
        default="en",
        description="Response language",
    )

    # 🟢 فلتر الإجابات: بيستخرج الأرقام من أي حاجة الموديل يبعتها (نص أو قائمة)
    @field_validator("responses", mode="before")
    @classmethod
    def force_list_of_ints(cls, v):
        if v is None or str(v).lower() == "null" or v == "":
            return [0] * 9  # Fallback آمن عشان ميكراشش

        if isinstance(v, list):
            # ينظف القائمة لو فيها نصوص يحولها لأرقام
            clean_list = []
            for item in v:
                try:
                    clean_list.append(int(item))
                except (ValueError, TypeError):
                    clean_list.append(0)
            return clean_list

        if isinstance(v, str):
            # لو الموديل بعتها كنص، بنستخرج كل الأرقام اللي فيه بالـ Regex
            import re

            numbers = re.findall(r"\d+", v)
            if numbers:
                return [int(num) for num in numbers]
            return [0] * 9

        return [0] * 9

    # 🟢 فلتر نوع التقييم (بيصلح اللخبطة)
    @field_validator("screening_type", mode="before")
    @classmethod
    def force_screening_type(cls, v):
        if v is None or str(v).lower() == "null":
            return "phq9"
        val_str = str(v).lower().strip()
        if "gad" in val_str:
            return "gad7"
        return "phq9"

    # 🟢 فلتر اللغة
    @field_validator("language", mode="before")
    @classmethod
    def force_language(cls, v):
        if v is None or str(v).lower() == "null":
            return "en"
        val_str = str(v).lower().strip()
        if "ar" in val_str or "عرب" in val_str:
            return "ar"
        return "en"


class MentalHealthScreener:
    """PHQ-9 and GAD-7 calculator with suicidality escalation."""

    _data = None

    @classmethod
    def _load(cls) -> dict:
        if cls._data is not None:
            return cls._data
        path = Path(__file__).resolve().parent.parent / "prompts" / "phq9_gad7.json"
        with open(path, encoding="utf-8") as f:
            cls._data = json.load(f)
        return cls._data

    def screen(
        self, responses: list[int], screening_type: str = "phq9", language: str = "en"
    ) -> dict[str, Any]:
        """Calculate score and determine severity band."""
        data = self._load()
        screening = data[screening_type]

        if len(responses) != len(screening["questions"]):
            return {
                "error": f"Expected {len(screening['questions'])} responses, got {len(responses)}"
            }

        total = sum(responses)

        # Find severity band
        result = None
        for band in screening["scoring"]:
            low, high = band["range"]
            if low <= total <= high:
                result = band
                break

        if not result:
            result = {"severity": "unknown", "label_en": "Unknown", "recommendation_en": ""}

        # Suicidality check (PHQ-9 question 9)
        has_suicidality = False
        crisis_resources = None
        if screening_type == "phq9" and len(responses) >= 9 and responses[8] > 0:
            has_suicidality = True
            crisis_resources = data["crisis_resources"]["egypt"]

        return {
            "score": total,
            "max_score": len(screening["questions"]) * 3,
            "severity": result["severity"],
            "label": result.get(f"label_{language}", result.get("label_en", "")),
            "recommendation": result.get(
                f"recommendation_{language}", result.get("recommendation_en", "")
            ),
            "has_suicidality": has_suicidality,
            "crisis_resources": crisis_resources,
            "screening_type": screening_type,
        }


class ScreenMentalHealthTool(Tool):
    """PHQ-9 and GAD-7 mental health screening tool."""

    def __init__(self):
        self._screener = MentalHealthScreener()

    @property
    def name(self) -> str:
        return "screen_mental_health"

    @property
    def description(self) -> str:
        return (
            "Screen for depression (PHQ-9) or anxiety (GAD-7) using validated questionnaires. "
            "Collect patient responses (0-3 scale per question), submit for scoring. "
            "PHQ-9 Q9 > 0 triggers suicidality alert with crisis hotline. "
            "For PHQ-9, ask all 9 questions. For GAD-7, ask all 7 questions. "
            "Ask one question at a time, record the response, then proceed."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return MentalHealthInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, MentalHealthInput):
            raise TypeError(f"Expected MentalHealthInput, got {type(input_data)}")
        return self._screener.screen(
            input_data.responses,
            input_data.screening_type,
            input_data.language,
        )
