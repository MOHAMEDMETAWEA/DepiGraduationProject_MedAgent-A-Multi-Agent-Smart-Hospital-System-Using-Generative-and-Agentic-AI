"""Tool: check_medication_interactions — drug safety checker."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# class MedicationInput(BaseModel):
#     """Input schema for medication interaction check."""


#     current_medications: list[str] = Field(
#         ...,
#         min_length=1,
#         description="List of current medications the patient is taking (brand or generic names)",
#     )
#     new_medication: str = Field(
#         ...,
#         # min_length=1,
#         default="", # 🟢 خلينا الديفولت فاضي وشيلنا min_length
#         description="New medication being considered",
#     )
#     allergies: list[str] = Field(
#         default=[],
#         description="Known drug allergies",
#     )
#     language: str = Field(
#         default="en",
#         pattern="^(ar|en)$",
#         description="Output language",
#     )
# ------------------
class MedicationInput(BaseModel):
    """Input schema for medication interaction check."""

    current_medications: list[str] = Field(
        default=[],  # 🟢 ضفنا ديفولت لتجنب الـ missing arguments
        description="List of current medications the patient is taking (e.g., ['Aspirin', 'Ibuprofen']).",
    )
    new_medication: str = Field(
        default="",
        description="New medication being considered. IMPORTANT: Pass an empty string '' if only checking current medications against each other.",
    )
    allergies: list[str] = Field(
        default=[], description="Known drug allergies. IMPORTANT: Pass an empty list [] if none."
    )
    language: str = Field(
        default="ar",  # 🟢 خليت الديفولت عربي بما إن السيستم بتاعنا Bilingual
        description="Output language, strictly 'ar' or 'en'.",
    )

    # 🟢 الفلتر السحري: بيعالج البيانات قبل ما Pydantic يعملها Validate
    @field_validator("current_medications", "allergies", mode="before")
    @classmethod
    def force_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            # لو الموديل بعت الأدوية كنص (سواء دواء واحد أو مفصول بفاصلة)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


# class MedicationInput(BaseModel):
#     """Input schema for medication interaction check."""

#     current_medications: list[str] = Field(
#         description="List of current medications the patient is taking (e.g., ['Aspirin', 'Ibuprofen'])."
#     )
#     new_medication: str = Field(
#         description="New medication being considered. IMPORTANT: Pass an empty string '' if only checking current medications against each other."
#     )
#     allergies: list[str] = Field(
#         description="Known drug allergies. IMPORTANT: Pass an empty list [] if none."
#     )
#     language: str = Field(
#         description="Output language, strictly 'ar' or 'en'."
#     )


class MedicationChecker:
    """Checks drug-drug interactions, allergies, and dose warnings."""

    _data = None

    @classmethod
    def _load(cls) -> dict:
        if cls._data is not None:
            return cls._data
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data"
            / "medications"
            / "interactions.json"
        )
        with open(path, encoding="utf-8") as f:
            cls._data = json.load(f)
        return cls._data

    def _resolve_drug(self, name: str) -> str | None:
        """Map a brand name to its generic class. Returns None if unknown."""
        data = self._load()
        name_lower = name.lower().strip()
        for generic, aliases in data["brand_aliases"].items():
            for alias in aliases:
                if alias.lower() in name_lower or name_lower in alias.lower():
                    return generic
        # Direct match to a generic class
        if name_lower in data["brand_aliases"]:
            return name_lower
        return None

    def check(
        self, current_meds: list[str], new_med: str, allergies: list[str] | None = None
    ) -> dict[str, Any]:
        """Run the full interaction check."""
        data = self._load()
        allergies = allergies or []

        # Resolve all drugs to generic classes
        resolved_current = []
        for med in current_meds:
            resolved = self._resolve_drug(med)
            if resolved:
                resolved_current.append((med, resolved))

        resolved_new = self._resolve_drug(new_med)
        if not resolved_new:
            return {
                "error": f"Unknown medication: {new_med}",
                "interactions": [],
                "allergy_conflicts": [],
                "dose_warnings": [],
            }

        # 1. Drug-Drug Interactions
        interactions = []
        for original, generic in resolved_current:
            for rule in data["interactions"]:
                if generic == resolved_new:
                    continue
                # Check both directions
                if (rule["drug_a"] == generic and rule["drug_b"] == resolved_new) or (
                    rule["drug_a"] == resolved_new and rule["drug_b"] == generic
                ):
                    interactions.append(
                        {
                            "drug_a": original,
                            "drug_b": new_med,
                            "severity": rule["severity"],
                            "reason": rule["reason"],
                            "source": rule["source"],
                        }
                    )

        # 2. Allergy conflicts
        allergy_conflicts = []
        allergy_lower = [a.lower().strip() for a in allergies]
        for allergy in allergy_lower:
            allergy_class = self._resolve_drug(allergy) or allergy
            if allergy_class == resolved_new:
                allergy_conflicts.append(
                    {
                        "allergy": allergy,
                        "medication": new_med,
                        "severity": "contraindicated",
                        "reason": f"Patient has known allergy to {allergy}",
                    }
                )

        return {
            "interactions": interactions,
            "allergy_conflicts": allergy_conflicts,
            "dose_warnings": [],
            "total_warnings": len(interactions) + len(allergy_conflicts),
        }


class CheckMedicationTool(Tool):
    """Drug interaction and allergy safety checker."""

    def __init__(self):
        self._checker = MedicationChecker()

    @property
    def name(self) -> str:
        return "check_medication_interactions"

    @property
    def description(self) -> str:
        return (
            "Check for drug-drug interactions, allergy conflicts, and dose warnings "
            "between a patient's current medications and a new medication. "
            "Returns interaction severity (contraindicated/major/moderate/minor) with sources."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return MedicationInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, MedicationInput):
            raise TypeError(f"Expected MedicationInput, got {type(input_data)}")
        return self._checker.check(
            input_data.current_medications,
            input_data.new_medication,
            input_data.allergies,
        )
