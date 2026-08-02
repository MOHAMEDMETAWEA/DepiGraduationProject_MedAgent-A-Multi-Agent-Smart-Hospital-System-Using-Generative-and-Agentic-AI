"""Tool: score_triage — Manchester Triage Scale scoring for the agent."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# ── Schema ──


# class TriageInput(BaseModel):
#     """Input schema for triage scoring."""


#     symptoms: list[str] = Field(
#         ...,  # ... = required
#         min_length=1,
#         description="List of patient symptoms as strings",
#     )
#     age: int | None = Field(
#         default=None,
#         ge=0,
#         description="Patient age in years (for age-adjusted scoring)",
#     )
#     comorbidities: list[str] | None = Field(
#         default=None,
#         description="Known chronic conditions (diabetes, heart disease, COPD, etc.)",
#     )
# -------------------------
class TriageInput(BaseModel):
    """Input schema for triage scoring."""

    symptoms: Any = Field(
        default=[],
        description="List of patient symptoms",
    )
    age: Any = Field(
        default=None,
        description="Patient age in years (for age-adjusted scoring)",
    )
    comorbidities: Any = Field(
        default=[],
        description="Known chronic conditions (diabetes, heart disease, COPD, etc.)",
    )

    # 🟢 الفلتر السحري للقوائم (الأعراض والأمراض)
    @field_validator("symptoms", "comorbidities", mode="before")
    @classmethod
    def force_list(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []

    # 🟢 الفلتر السحري للأرقام (العمر)
    @field_validator("age", mode="before")
    @classmethod
    def force_int(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return None
        try:
            return int(
                float(v)
            )  # بنحول لـ float الأول عشان لو الموديل بعت "3.5" مثلاً، يقبلها ويخليها 3
        except (ValueError, TypeError):
            return None


# ── Scorer Logic ──


class TriageScorer:
    """Manchester Triage Scale scorer with age and comorbidity adjustments."""

    _rules = None

    @classmethod
    def _load_rules(cls) -> dict:
        if cls._rules is not None:
            return cls._rules
        yaml_path = Path(__file__).resolve().parent.parent / "safety" / "triage_rules.yaml"
        with open(yaml_path, encoding="utf-8") as f:
            cls._rules = yaml.safe_load(f)
        return cls._rules

    def score(
        self,
        symptoms: list[str],
        age: int | None = None,
        comorbidities: list[str] | None = None,
        red_flags_detected: bool = False,
    ) -> dict[str, Any]:
        """
        Calculate triage score based on symptoms.

        Parameters
        ----------
        symptoms : list[str]
            Patient-reported symptoms.
        age : int or None
            Patient age for age-adjusted risk.
        comorbidities : list[str] or None
            Known chronic conditions.
        red_flags_detected : bool
            If True, forces emergency level regardless of scoring.

        Returns
        -------
        dict
            level, score, reasoning, adjustments
        """
        # Red flags override everything
        if red_flags_detected:
            return {
                "level": "emergency",
                "score": 100,
                "reasoning": "Red flag(s) detected — emergency escalation required",
                "matched_rules": [],
                "adjustments": [],
            }

        data = self._load_rules()
        text_lower = " ".join(symptoms).lower()

        # 1. Match symptom keywords against triage rules
        matched_rules = []
        for rule in data["rules"]:
            # كل keywords في الـ rule لازم تكون موجودة في النص؟
            if all(kw.lower() in text_lower for kw in rule["keywords"]):
                matched_rules.append(rule)

        if not matched_rules:
            # Default: low urgency, recommend GP visit
            return {
                "level": "routine",
                "score": 10,
                "reasoning": "No triage rules matched — recommend routine evaluation with primary care",
                "matched_rules": [],
                "adjustments": [],
            }

        # 2. Take the highest-scoring rule as base
        best = max(matched_rules, key=lambda r: r["score"])
        final_score = best["score"]
        final_level = best["level"]
        reasoning_parts = [best["reason"]]
        adjustments = []

        # 3. Age adjustment
        if age is not None:
            for adj in data.get("age_adjustments", []):
                low, high = adj["range"].split("-")
                if int(low) <= age <= int(high):
                    final_score += adj["adjustment"]
                    adjustments.append(
                        {
                            "type": "age",
                            "detail": f"Age {age}: +{adj['adjustment']} ({adj['reason']})",
                        }
                    )
                    reasoning_parts.append(adj["reason"])

        # 4. Comorbidity adjustments
        if comorbidities:
            for cond in comorbidities:
                cond_lower = cond.lower()
                for adj in data.get("comorbidity_adjustments", []):
                    if adj["condition"].lower() in cond_lower:
                        final_score += adj["adjustment"]
                        adjustments.append(
                            {
                                "type": "comorbidity",
                                "detail": f"{cond}: +{adj['adjustment']} ({adj['reason']})",
                            }
                        )
                        reasoning_parts.append(adj["reason"])

        # Cap score at 100
        final_score = min(final_score, 100)

        # Re-evaluate level if score crossed threshold
        if final_score >= 80:
            final_level = "emergency"
        elif final_score >= 50:
            final_level = "urgent"
        else:
            final_level = "routine"

        return {
            "level": final_level,
            "score": final_score,
            "reasoning": " | ".join(reasoning_parts),
            "matched_rules": [r["reason"] for r in matched_rules[:3]],
            "adjustments": adjustments,
        }


# ── Tool ──


class ScoreTriageTool(Tool):
    """Manchester Triage Scale scoring tool for the agent."""

    def __init__(self, red_flag_tool=None):
        self._scorer = TriageScorer()
        self._red_flag_tool = red_flag_tool  # optional — للدمج مع T2.06

    @property
    def name(self) -> str:
        return "score_triage"

    @property
    def description(self) -> str:
        return (
            "Score patient symptoms using Manchester Triage Scale. "
            "Returns triage level (emergency/urgent/routine), score (0-100), "
            "and clinical reasoning. Provide symptoms list and optionally age "
            "and known comorbidities for adjusted scoring."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return TriageInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, TriageInput):
            raise TypeError(f"Expected TriageInput, got {type(input_data)}")

        return self._scorer.score(
            symptoms=input_data.symptoms,
            age=input_data.age,
            comorbidities=input_data.comorbidities,
            red_flags_detected=False,  # Agent passes this before calling
        )
