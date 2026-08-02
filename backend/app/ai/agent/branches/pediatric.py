"""Pediatric safety branch — auto-switches agent context for patients under 18."""

from dataclasses import dataclass


@dataclass
class PediatricContext:
    """Holds pediatric-specific patient context for the agent."""

    age_months: float
    weight_kg: float | None = None

    @classmethod
    def from_dob(cls, dob_str: str) -> "PediatricContext | None":
        """Build from date-of-birth string (ISO format YYYY-MM-DD). Returns None if age >= 18."""
        from datetime import date

        try:
            dob = date.fromisoformat(dob_str)
            today = date.today()
            age_months = (today.year - dob.year) * 12 + (today.month - dob.month)
            if age_months >= 18 * 12:
                return None
            return cls(age_months=float(age_months))
        except (ValueError, TypeError):
            return None

    @classmethod
    def from_age_years(cls, age_years: float) -> "PediatricContext | None":
        """Build from age in years. Returns None if age >= 18."""
        if age_years >= 18:
            return None
        return cls(age_months=age_years * 12)

    @property
    def is_neonate(self) -> bool:
        return self.age_months < 1

    @property
    def is_young_infant(self) -> bool:
        """Infants under 3 months — highest risk group."""
        return self.age_months < 3

    @property
    def is_infant(self) -> bool:
        return self.age_months < 12

    @property
    def age_years(self) -> float:
        return self.age_months / 12

    @property
    def age_label(self) -> str:
        if self.is_neonate:
            return "newborn"
        if self.is_infant:
            return f"infant ({int(self.age_months)}mo)"
        return f"child ({self.age_years:.1f}y)"

    def system_prompt_key(self, language: str) -> str:
        """Return the prompt key to load from agent/prompts/."""
        return f"{language}_pediatric"

    def safety_tool_input(self, symptoms: list[str], medications: list[str], language: str) -> dict:
        """Build input dict for the assess_pediatric_safety tool."""
        return {
            "age_months": self.age_months,
            "weight_kg": self.weight_kg,
            "symptoms": symptoms,
            "medications": medications,
            "language": language,
        }
