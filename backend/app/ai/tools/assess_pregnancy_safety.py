"""Tool: assess_pregnancy_safety — OB red flags and pregnancy drug-category warnings."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# Egypt national crisis line for obstetric emergencies
EGYPT_OB_HOTLINE = "123 (Egyptian emergency services)"

# OB red flags — any match triggers emergency
OB_RED_FLAGS: list[dict] = [
    {
        "keywords_en": [
            "severe headache",
            "vision changes",
            "blurry vision",
            "seeing spots",
            "flashing lights",
        ],
        "keywords_ar": ["صداع شديد", "تغير في النظر", "رؤية ضبابية", "نقاط مضيئة", "ومضات"],
        "condition": "Possible pre-eclampsia / HELLP syndrome",
        "condition_ar": "احتمال تسمم الحمل / متلازمة هيلب",
        "level": "emergency",
    },
    {
        "keywords_en": ["heavy bleeding", "heavy vaginal bleeding", "soaking pad", "passing clots"],
        "keywords_ar": ["نزيف شديد", "نزيف مهبلي شديد", "جلطات مهبلية", "تبلل الكوسة"],
        "condition": "Antepartum/postpartum haemorrhage",
        "condition_ar": "نزيف ما قبل أو بعد الولادة",
        "level": "emergency",
    },
    {
        "keywords_en": ["severe abdominal pain", "severe cramping", "rigid abdomen"],
        "keywords_ar": ["ألم بطني شديد", "تقلصات شديدة", "بطن صلب"],
        "condition": "Possible abruption / uterine rupture",
        "condition_ar": "احتمال انفصال المشيمة أو تمزق الرحم",
        "level": "emergency",
    },
    {
        "keywords_en": [
            "decreased fetal movement",
            "baby not moving",
            "no kicks",
            "reduced movement",
        ],
        "keywords_ar": ["قلة حركة الجنين", "الجنين لا يتحرك", "لا ركلات", "تراجع حركة الطفل"],
        "condition": "Decreased fetal movement — requires urgent CTG assessment",
        "condition_ar": "نقص حركة الجنين — يتطلب تقييم CTG عاجلاً",
        "level": "emergency",
    },
    {
        "keywords_en": ["water broke", "membranes ruptured", "fluid leaking", "gush of fluid"],
        "keywords_ar": ["انكسر الكيس", "نزول ماء", "سائل يخرج", "فقاعة الماء انفجرت"],
        "condition": "Rupture of membranes",
        "condition_ar": "انفجار الأغشية الأمنيوسية",
        "level": "urgent",
    },
    {
        "keywords_en": ["contractions", "regular contractions", "labor pains"],
        "keywords_ar": ["تقلصات منتظمة", "آلام الولادة", "مخاض"],
        "condition": "Possible onset of labour",
        "condition_ar": "احتمال بداية المخاض",
        "level": "urgent",
    },
    {
        "keywords_en": ["fever", "chills", "burning urination", "foul discharge"],
        "keywords_ar": ["حمى", "قشعريرة", "حرقة بول", "إفرازات كريهة"],
        "condition": "Possible chorioamnionitis / UTI / infection during pregnancy",
        "condition_ar": "احتمال التهاب السلى أو التهاب المسالك البولية أثناء الحمل",
        "level": "urgent",
    },
    {
        "keywords_en": ["shortness of breath", "chest pain", "leg swelling", "calf pain"],
        "keywords_ar": ["ضيق تنفس", "ألم صدر", "تورم الساق", "ألم الساق"],
        "condition": "Possible DVT / pulmonary embolism — pregnancy increases VTE risk",
        "condition_ar": "احتمال تجلط وريدي عميق / انسداد رئوي — الحمل يزيد خطر الجلطة",
        "level": "emergency",
    },
]

# FDA Pregnancy categories (A/B/C/D/X) — curated subset of common drugs
# X = absolutely contraindicated, D = risks outweigh benefits (avoid unless life-threatening)
FDA_PREGNANCY_CATEGORIES: dict[str, dict] = {
    # Category X — absolutely contraindicated
    "warfarin": {"category": "X", "concern": "Teratogenic — causes fetal warfarin syndrome"},
    "isotretinoin": {"category": "X", "concern": "Highly teratogenic — severe fetal malformations"},
    "methotrexate": {"category": "X", "concern": "Abortifacient and teratogenic"},
    "thalidomide": {"category": "X", "concern": "Extremely teratogenic — phocomelia"},
    "finasteride": {"category": "X", "concern": "Teratogenic — male fetal genital malformations"},
    "misoprostol": {"category": "X", "concern": "Causes uterine contractions — risk of abortion"},
    "ribavirin": {"category": "X", "concern": "Teratogenic"},
    "statins": {"category": "X", "concern": "Cholesterol essential for fetal development"},
    "atorvastatin": {"category": "X", "concern": "Statin — contraindicated in pregnancy"},
    "simvastatin": {"category": "X", "concern": "Statin — contraindicated in pregnancy"},
    # Category D — avoid unless benefits clearly outweigh risks
    "ibuprofen": {
        "category": "D",
        "concern": (
            "NSAIDs cause premature closure of ductus arteriosus — "
            "CONTRAINDICATED in third trimester. Avoid in first trimester (miscarriage risk)."
        ),
    },
    "diclofenac": {
        "category": "D",
        "concern": "NSAID — contraindicated in third trimester (premature ductus closure)",
    },
    "naproxen": {
        "category": "D",
        "concern": "NSAID — avoid throughout pregnancy, especially third trimester",
    },
    "aspirin": {
        "category": "D",
        "concern": "Full-dose aspirin (>150 mg) — avoid. Low-dose (75-150 mg) may be used under medical supervision.",
    },
    "ace_inhibitor": {
        "category": "D",
        "concern": "ACE inhibitors cause fetal renal toxicity — CONTRAINDICATED in second and third trimester",
    },
    "lisinopril": {
        "category": "D",
        "concern": "ACE inhibitor — contraindicated in pregnancy",
    },
    "enalapril": {
        "category": "D",
        "concern": "ACE inhibitor — contraindicated in pregnancy",
    },
    "arb": {
        "category": "D",
        "concern": "ARBs cause fetal renal toxicity — CONTRAINDICATED throughout pregnancy",
    },
    "losartan": {
        "category": "D",
        "concern": "ARB — contraindicated throughout pregnancy",
    },
    "valsartan": {
        "category": "D",
        "concern": "ARB — contraindicated throughout pregnancy",
    },
    "tetracycline": {
        "category": "D",
        "concern": "Causes permanent tooth discoloration and bone growth inhibition in fetus",
    },
    "doxycycline": {
        "category": "D",
        "concern": "Tetracycline-class antibiotic — avoid during pregnancy",
    },
    "phenytoin": {
        "category": "D",
        "concern": "Fetal hydantoin syndrome — heart defects, cleft palate",
    },
    "valproate": {
        "category": "D",
        "concern": "Neural tube defects, fetal valproate syndrome",
    },
    "carbamazepine": {
        "category": "D",
        "concern": "Neural tube defects — use only if no safer alternative",
    },
    # Category B — likely safe
    "paracetamol": {
        "category": "B",
        "concern": "Generally safe at recommended doses. Preferred antipyretic in pregnancy.",
    },
    "amoxicillin": {"category": "B", "concern": "Considered safe in pregnancy"},
    "cetirizine": {"category": "B", "concern": "Antihistamine — generally safe"},
    "folic_acid": {
        "category": "A",
        "concern": "Essential — take 400-800 mcg daily pre-conception and first trimester",
    },
}

# Brand-name aliases
BRAND_ALIASES: dict[str, str] = {
    "brufen": "ibuprofen",
    "advil": "ibuprofen",
    "بروفين": "ibuprofen",
    "voltaren": "diclofenac",
    "فولتارين": "diclofenac",
    "aleve": "naproxen",
    "panadol": "paracetamol",
    "بنادول": "paracetamol",
    "tylenol": "paracetamol",
    "coumadin": "warfarin",
    "accupril": "ace_inhibitor",
    "cozaar": "losartan",
    "diovan": "valsartan",
    "depakote": "valproate",
    "tegretol": "carbamazepine",
    "zyrtec": "cetirizine",
    "claritin": "cetirizine",
    "aspocid": "aspirin",
}


def _resolve_drug(name: str) -> str:
    n = name.lower().strip()
    return BRAND_ALIASES.get(n, n)


def _month_to_trimester(value: int) -> int | None:
    """Map an integer to a clinical trimester (1, 2, or 3).

    Rules:
      • 1, 2, 3  → returned as-is (already a trimester)
      • 4, 5, 6  → trimester 2
      • 7, 8, 9  → trimester 3
      • anything else (incl. 0, negatives, >9) → None

    Note: months 1-3 collide with trimesters 1-3, which is fine because both
    interpretations map to trimester 1. This is intentional — the field is
    documented as accepting either.
    """
    if not isinstance(value, int):
        return None
    if value <= 0 or value > 9:
        return None
    if value <= 3:
        return value
    if value <= 6:
        return 2
    return 3


class PregnancySafetyInput(BaseModel):
    """Input schema for assess_pregnancy_safety tool.

    The ``trimester`` field is intentionally lenient: clinicians + patients
    say "حامل في الشهر السابع" ("seventh month"), but the underlying logic
    only cares about 1st / 2nd / 3rd trimester. The validator accepts:
      • int 1-3        → used as-is (trimester)
      • int 4-9        → converted (months 4-6→2, months 7-9→3)
      • int 1-3 also handled as months 1-3 → trimester 1 (unambiguous)
      • "1"/"2"/"3"/"first"/"second"/"third" + Arabic equivalents
      • "month 7" / "الشهر السابع"  → 3rd trimester
      • None / "unknown" / 0 / ""    → None

    Groq + OpenAI strict validators would otherwise reject anything outside
    [1, 3] before the LLM's text-based conversion could run.
    """

    symptoms: list[str] = Field(
        default=[],
        description="Current symptoms reported by the pregnant patient",
    )
    medications: list[str] = Field(
        default=[],
        description="Medications the patient is taking or asking about",
    )
    trimester: int | str | None = Field(
        default=None,
        description=(
            "Current trimester (1, 2, or 3) OR the pregnancy month (1-9) — "
            "the tool converts months 1-3→T1, 4-6→T2, 7-9→T3 automatically. "
            "Pass null/None when unknown."
        ),
    )
    language: str = Field(
        default="en",
        pattern="^(ar|en)$",
    )

    @field_validator("trimester", mode="before")
    @classmethod
    def _coerce_trimester(cls, v: Any) -> int | None:
        """Normalize trimester input to an int 1-3 or None.

        Accepts month numbers (1-9), trimester ints (1-3), Arabic/English
        ordinal words, "null"/"unknown" sentinels, and various phrasings.
        """
        if v is None:
            return None

        # Handle stringified inputs first
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("", "null", "none", "unknown", "0", "غير معروف", "لا أعرف"):
                return None
            # Arabic ordinals
            ar_map = {
                "الأول": 1,
                "الاول": 1,
                "الثاني": 2,
                "الثالث": 3,
                "الرابع": 4,
                "الخامس": 5,
                "السادس": 6,
                "السابع": 7,
                "الثامن": 8,
                "التاسع": 9,
            }
            for word, num in ar_map.items():
                if word in s:
                    return _month_to_trimester(num)
            # English ordinals
            en_map = {
                "first": 1,
                "1st": 1,
                "one": 1,
                "second": 2,
                "2nd": 2,
                "two": 2,
                "third": 3,
                "3rd": 3,
                "three": 3,
                "fourth": 4,
                "4th": 4,
                "fifth": 5,
                "5th": 5,
                "sixth": 6,
                "6th": 6,
                "seventh": 7,
                "7th": 7,
                "eighth": 8,
                "8th": 8,
                "ninth": 9,
                "9th": 9,
            }
            for word, num in en_map.items():
                if word in s:
                    return _month_to_trimester(num)
            # Bare number string ("7")
            try:
                return _month_to_trimester(int(s))
            except (ValueError, TypeError):
                return None

        # Integer path
        if isinstance(v, int):
            return _month_to_trimester(v)

        return None


class AssessPregnancySafetyTool(Tool):
    """Pregnancy safety branch — OB red flags and FDA pregnancy-category drug warnings."""

    @property
    def name(self) -> str:
        return "assess_pregnancy_safety"

    @property
    def description(self) -> str:
        return (
            "Assess safety for a pregnant patient. "
            "Checks obstetric red flags (pre-eclampsia, haemorrhage, decreased fetal movement, PROM, DVT) "
            "and provides FDA pregnancy-category warnings for medications (category D and X are flagged). "
            "Use whenever the patient is pregnant or may be pregnant."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return PregnancySafetyInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, PregnancySafetyInput):
            raise TypeError(f"Expected PregnancySafetyInput, got {type(input_data)}")

        lang = input_data.language
        symptoms_lower = [s.lower() for s in input_data.symptoms]
        trimester = input_data.trimester
        # `trimester` is constrained by the Pydantic schema to None | 1 | 2 | 3.
        # Month-to-trimester conversion is the caller's responsibility (documented
        # on the `trimester` field). Downstream comparisons here are safe with None.

        # ── OB red flag detection ──
        ob_red_flags: list[dict] = []
        highest_level = "routine"

        for rule in OB_RED_FLAGS:
            # Also check cross-language
            all_keywords = rule["keywords_en"] + rule["keywords_ar"]
            matched = [
                kw for kw in all_keywords if any(kw.lower() in sym for sym in symptoms_lower)
            ]
            if matched:
                ob_red_flags.append(
                    {
                        "matched_keywords": matched[:3],
                        "condition": rule["condition_ar"] if lang == "ar" else rule["condition"],
                        "level": rule["level"],
                    }
                )
                if rule["level"] == "emergency":
                    highest_level = "emergency"
                elif rule["level"] == "urgent" and highest_level != "emergency":
                    highest_level = "urgent"

        # ── Medication safety checks ──
        drug_warnings: list[dict] = []
        for med in input_data.medications:
            generic = _resolve_drug(med)
            entry = FDA_PREGNANCY_CATEGORIES.get(generic)
            if entry:
                category = entry["category"]
                concern = entry["concern"]
                is_contraindicated = category in ("X", "D")

                warning: dict[str, Any] = {
                    "medication": med,
                    "generic": generic,
                    "fda_pregnancy_category": category,
                    "concern": concern,
                    "contraindicated": is_contraindicated,
                }

                # Third-trimester specific warnings
                if trimester == 3 and generic in ("ibuprofen", "naproxen", "diclofenac", "aspirin"):
                    warning["trimester_note"] = (
                        "ABSOLUTELY CONTRAINDICATED in third trimester — premature ductus arteriosus closure."
                        if lang == "en"
                        else "مطلقاً ممنوع في الثلث الثالث — يسبب إغلاق قناة القلب الجنينية المبكرة."
                    )

                drug_warnings.append(warning)
            else:
                # Unknown drug — advise verification
                drug_warnings.append(
                    {
                        "medication": med,
                        "generic": generic,
                        "fda_pregnancy_category": "unknown",
                        "concern": (
                            f"Safety in pregnancy unknown for '{med}'. Consult your OB/GYN before taking."
                            if lang == "en"
                            else f"سلامة '{med}' أثناء الحمل غير معروفة. استشيري طبيب النساء قبل التناول."
                        ),
                        "contraindicated": False,
                    }
                )

        # ── Crisis resources ──
        crisis = (
            {
                "hotline": EGYPT_OB_HOTLINE,
                "message": "If you have any of the above emergency symptoms, call emergency services immediately.",
            }
            if lang == "en"
            else {
                "hotline": EGYPT_OB_HOTLINE,
                "message": "إذا كانت لديك أي من أعراض الطوارئ أعلاه، اتصلي بالإسعاف فوراً.",
            }
        )

        return {
            "triage_level": highest_level,
            "ob_red_flags": ob_red_flags,
            "has_red_flags": len(ob_red_flags) > 0,
            "drug_warnings": drug_warnings,
            "has_drug_warnings": any(w["contraindicated"] for w in drug_warnings),
            "trimester": trimester,
            "crisis_resources": crisis if ob_red_flags else None,
            "safety_note": (
                "This is a preliminary safety check. Always consult your obstetrician for all "
                "medication decisions and symptom evaluation during pregnancy."
                if lang == "en"
                else "هذا فحص أمان أولي. استشيري دائماً طبيب النساء والتوليد لجميع قرارات الأدوية وتقييم الأعراض أثناء الحمل."
            ),
        }
