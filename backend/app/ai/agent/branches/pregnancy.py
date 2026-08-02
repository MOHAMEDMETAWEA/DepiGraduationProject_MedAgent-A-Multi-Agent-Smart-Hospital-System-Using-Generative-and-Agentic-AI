"""Pregnancy safety branch — auto-switches agent context for pregnant patients."""

from dataclasses import dataclass, field

# Keywords that trigger pregnancy branch detection from conversation text
PREGNANCY_KEYWORDS: list[str] = [
    # English
    "pregnant",
    "pregnancy",
    "trimester",
    "first trimester",
    "second trimester",
    "third trimester",
    "ob/gyn",
    "obstetrician",
    "antenatal",
    "prenatal",
    "expecting",
    "due date",
    "gestational",
    "fetus",
    "baby bump",
    "maternity",
    "birth",
    "labour",
    "labor",
    # Arabic
    "حامل",
    "حمل",
    "الثلث الأول",
    "الثلث الثاني",
    "الثلث الثالث",
    "طبيب نساء",
    "متابعة الحمل",
    "جنين",
    "موعد الولادة",
    "أسابيع حمل",
    "شهور حمل",
]


@dataclass
class PregnancyContext:
    """Holds pregnancy-specific context for the agent."""

    trimester: int | None = None
    gestational_weeks: int | None = None
    medications: list[str] = field(default_factory=list)

    @classmethod
    def detect_from_text(cls, text: str) -> "PregnancyContext | None":
        """Return PregnancyContext if pregnancy keywords found in text, else None."""
        text_lower = text.lower()
        if not any(kw.lower() in text_lower for kw in PREGNANCY_KEYWORDS):
            return None
        ctx = cls()
        ctx.trimester = _extract_trimester(text_lower)
        ctx.gestational_weeks = _extract_weeks(text_lower)
        return ctx

    @property
    def trimester_label(self) -> str:
        if self.trimester == 1:
            return "first trimester (0-12 weeks)"
        if self.trimester == 2:
            return "second trimester (13-26 weeks)"
        if self.trimester == 3:
            return "third trimester (27-40 weeks)"
        if self.gestational_weeks:
            return f"{self.gestational_weeks} weeks gestation"
        return "pregnancy (trimester unknown)"

    def system_prompt_key(self, language: str) -> str:
        """Return the prompt key to load from agent/prompts/."""
        return f"{language}_pregnancy"

    def safety_tool_input(self, symptoms: list[str], medications: list[str], language: str) -> dict:
        """Build input dict for the assess_pregnancy_safety tool."""
        return {
            "symptoms": symptoms,
            "medications": medications or self.medications,
            "trimester": self.trimester,
            "language": language,
        }


def _extract_trimester(text: str) -> int | None:
    import re

    m = re.search(r"\b(first|1st|second|2nd|third|3rd|أول|ثاني|ثالث)\s*(trimester|ثلث)\b", text)
    if not m:
        weeks = _extract_weeks(text)
        if weeks:
            if weeks <= 12:
                return 1
            if weeks <= 26:
                return 2
            return 3
        return None
    label = m.group(1).lower()
    mapping = {
        "first": 1,
        "1st": 1,
        "أول": 1,
        "second": 2,
        "2nd": 2,
        "ثاني": 2,
        "third": 3,
        "3rd": 3,
        "ثالث": 3,
    }
    return mapping.get(label)


def _extract_weeks(text: str) -> int | None:
    import re

    m = re.search(r"(\d{1,2})\s*(?:weeks?\s*(?:pregnant|gestation|حمل)|أسبوع\s*حمل)", text)
    if m:
        return int(m.group(1))
    return None
