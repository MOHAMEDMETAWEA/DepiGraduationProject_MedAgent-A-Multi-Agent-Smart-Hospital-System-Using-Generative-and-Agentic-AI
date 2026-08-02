"""Tool: assess_pediatric_safety — age-aware dose checks and pediatric red flags."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool

# Age-appropriate red flags by age band (age in years)
PEDIATRIC_RED_FLAGS: list[dict] = [
    # Neonates / Young infants (< 3 months)
    {
        "age_max_months": 3,
        "flags": [
            "fever",
            "حرارة",
            "سخونية",
            "temperature",
            "won't eat",
            "lethargic",
            "خامل",
            "لا يرضع",
            "bulging fontanelle",
            "يافوخ منتفخ",
            "high-pitched cry",
            "بكاء حاد",
        ],
        "level": "emergency",
        "reason": "Infants < 3 months with fever or lethargy require immediate emergency evaluation.",
        "reason_ar": "الأطفال دون 3 أشهر الذين يعانون من حرارة أو خمول يحتاجون تقييماً طارئاً فورياً.",
    },
    # All ages
    {
        "age_max_months": None,
        "flags": [
            "seizure",
            "تشنج",
            "convulsion",
            "اختلاج",
            "not breathing",
            "لا يتنفس",
            "blue lips",
            "شفاه زرقاء",
            "neck stiffness",
            "تصلب الرقبة",
            "non-blanching rash",
            "طفح لا يزول بالضغط",
            "purple rash",
            "طفح أرجواني",
            "unresponsive",
            "فاقد الوعي",
            "floppy",
            "مرتخي",
            "severe breathing difficulty",
            "صعوبة تنفس شديدة",
            "dehydration",
            "جفاف شديد",
            "sunken eyes",
            "عيون غائرة",
            "no wet diapers",
            "لا حفاضات مبللة",
        ],
        "level": "emergency",
        "reason": "Serious sign in a child — seek emergency care immediately.",
        "reason_ar": "علامة خطيرة عند الطفل — اطلب الرعاية الطارئة فوراً.",
    },
]

# Common pediatric medications with weight-based dosing (mg/kg) — curated subset
# Structured as: generic_name → {dose_per_kg, max_single_dose_mg, route, notes}
PEDIATRIC_DOSE_TABLE: dict[str, dict] = {
    "paracetamol": {
        "dose_per_kg": 15,
        "max_single_dose_mg": 1000,
        "max_daily_mg_per_kg": 75,
        "routes": ["oral", "rectal"],
        "min_age_months": 0,
        "notes_en": "Safest antipyretic in children. Repeat every 4-6 hours.",
        "notes_ar": "أكثر خافضات الحرارة أماناً للأطفال. يكرر كل 4-6 ساعات.",
    },
    "ibuprofen": {
        "dose_per_kg": 10,
        "max_single_dose_mg": 400,
        "max_daily_mg_per_kg": 40,
        "routes": ["oral"],
        "min_age_months": 6,
        "notes_en": "Do NOT use in infants < 6 months. Avoid in dehydration/renal disease.",
        "notes_ar": "لا تستخدم في الرضع دون 6 أشهر. تجنب في الجفاف وأمراض الكلى.",
    },
    "amoxicillin": {
        "dose_per_kg": 40,
        "max_single_dose_mg": 500,
        "max_daily_mg_per_kg": 90,
        "routes": ["oral"],
        "min_age_months": 0,
        "notes_en": "Standard dosing for AOM and mild pneumonia.",
        "notes_ar": "الجرعة القياسية لالتهاب الأذن الوسطى والالتهاب الرئوي الخفيف.",
    },
    "azithromycin": {
        "dose_per_kg": 10,
        "max_single_dose_mg": 500,
        "max_daily_mg_per_kg": 10,
        "routes": ["oral"],
        "min_age_months": 6,
        "notes_en": "Day 1 only (loading dose). Used for atypical pneumonia.",
        "notes_ar": "اليوم الأول فقط (جرعة تحميل). يستخدم للالتهاب الرئوي اللانمطي.",
    },
    "oral_rehydration_solution": {
        "dose_per_kg": 10,  # 10 ml/kg per hour for mild dehydration
        "max_single_dose_mg": None,
        "routes": ["oral"],
        "min_age_months": 0,
        "notes_en": "10 ml/kg over 1 hour for mild dehydration. 20 ml/kg for moderate.",
        "notes_ar": "10 مل/كجم خلال ساعة للجفاف الخفيف. 20 مل/كجم للجفاف المتوسط.",
    },
}

# Brand-name aliases → generic
BRAND_ALIASES: dict[str, str] = {
    "tylenol": "paracetamol",
    "panadol": "paracetamol",
    "calpol": "paracetamol",
    "بنادول": "paracetamol",
    "بروفين": "ibuprofen",
    "advil": "ibuprofen",
    "brufen": "ibuprofen",
    "augmentin": "amoxicillin",
    "amoxil": "amoxicillin",
    "zithromax": "azithromycin",
    "زيثروماكس": "azithromycin",
    "ors": "oral_rehydration_solution",
    "pedialyte": "oral_rehydration_solution",
}


def _resolve_drug(name: str) -> str:
    n = name.lower().strip()
    return BRAND_ALIASES.get(n, n)


# class PediatricSafetyInput(BaseModel):
#     """Input schema for assess_pediatric_safety tool."""

#     age_months: float = Field(
#         ...,
#         ge=0,
#         le=216,
#         description="Patient age in months (0 = newborn, 12 = 1 year, 216 = 18 years)",
#     )
#     weight_kg: float | None = Field(
#         default=None,
#         ge=0.5,
#         le=150,
#         description="Patient weight in kg (required for dose calculations)",
#     )
#     symptoms: list[str] = Field(
#         default=[],
#         description="Current symptoms reported by the patient or parent",
#     )
#     medications: list[str] = Field(
#         default=[],
#         description="Medications being considered or already given",
#     )
#     language: str = Field(
#         default="en",
#         pattern="^(ar|en)$",
#     )
# -------------------------


class PediatricSafetyInput(BaseModel):
    """Input schema for assess_pediatric_safety tool."""

    # 🟢 السر هنا: استخدام Any بيمنع Groq من إنه يرفض الريكويست لو الموديل بعت String
    age_months: Any = Field(
        default=0.0,
        description="Patient age in months (0 = newborn, 12 = 1 year, 216 = 18 years)",
    )
    weight_kg: Any = Field(
        default=None,
        description="Patient weight in kg",
    )
    symptoms: Any = Field(
        default=[],
        description="Current symptoms reported by the patient or parent",
    )
    medications: Any = Field(
        default=[],
        description="Medications being considered or already given",
    )
    language: Any = Field(
        default="ar",
    )

    # 🟢 الفلتر بتاعنا هيستلم الـ Any ويحوله لقائمة صحيحة
    @field_validator("symptoms", "medications", mode="before")
    @classmethod
    def force_list(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []

    # 🟢 الفلتر هيستلم الـ Any ويحوله لرقم صحيح
    @field_validator("age_months", "weight_kg", mode="before")
    @classmethod
    def force_float(cls, v):
        if v is None or str(v).lower() == "null" or str(v).strip() == "":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0


class AssessPediatricSafetyTool(Tool):
    """Pediatric safety branch — age-appropriate red flags and weight-based dose checks."""

    @property
    def name(self) -> str:
        return "assess_pediatric_safety"

    @property
    def description(self) -> str:
        return (
            "Assess pediatric safety for a child patient. "
            "Checks age-appropriate red flags (e.g., fever in infants < 3 months = emergency), "
            "and provides weight-based dose verification for common pediatric medications. "
            "Use whenever the patient is under 18 years old."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return PediatricSafetyInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, PediatricSafetyInput):
            raise TypeError(f"Expected PediatricSafetyInput, got {type(input_data)}")

        age_months = input_data.age_months
        weight_kg = input_data.weight_kg
        symptoms_lower = [s.lower() for s in input_data.symptoms]
        lang = input_data.language

        red_flags_found: list[dict] = []
        highest_level = "routine"

        # Check red flags
        for rule in PEDIATRIC_RED_FLAGS:
            if rule["age_max_months"] is not None and age_months > rule["age_max_months"]:
                continue
            matched = [
                kw for kw in rule["flags"] if any(kw.lower() in sym for sym in symptoms_lower)
            ]
            if matched:
                red_flags_found.append(
                    {
                        "matched_keywords": matched,
                        "level": rule["level"],
                        "reason": rule["reason_ar"] if lang == "ar" else rule["reason"],
                    }
                )
                if rule["level"] == "emergency":
                    highest_level = "emergency"
                elif rule["level"] == "urgent" and highest_level != "emergency":
                    highest_level = "urgent"

        # Dose checks
        dose_assessments: list[dict] = []
        for med in input_data.medications:
            generic = _resolve_drug(med)
            if generic in PEDIATRIC_DOSE_TABLE:
                entry = PEDIATRIC_DOSE_TABLE[generic]
                min_age = entry.get("min_age_months", 0)
                assessment: dict[str, Any] = {
                    "medication": med,
                    "generic": generic,
                    "routes": entry["routes"],
                    "notes": entry["notes_ar"] if lang == "ar" else entry["notes_en"],
                }

                # Age restriction check
                if age_months < min_age:
                    assessment["warning"] = (
                        f"NOT recommended for age < {min_age} months."
                        if lang == "en"
                        else f"غير موصى به لمن هم دون {min_age} شهراً."
                    )
                    assessment["safe"] = False
                else:
                    assessment["safe"] = True

                # Weight-based dose calculation
                if weight_kg and entry["dose_per_kg"]:
                    calculated_mg = round(weight_kg * entry["dose_per_kg"], 1)
                    max_mg = entry.get("max_single_dose_mg")
                    dose_mg = min(calculated_mg, max_mg) if max_mg else calculated_mg
                    assessment["calculated_dose_mg"] = dose_mg
                    assessment["dose_basis"] = (
                        f"{entry['dose_per_kg']} mg/kg × {weight_kg} kg = {calculated_mg} mg"
                        f"{f' (capped at {max_mg} mg max)' if max_mg and calculated_mg > max_mg else ''}"
                    )

                dose_assessments.append(assessment)

        # Age context
        if age_months < 1:
            age_label = "neonate" if lang == "en" else "مولود جديد"
        elif age_months < 12:
            age_label = (
                f"infant ({int(age_months)}mo)" if lang == "en" else f"رضيع ({int(age_months)} شهر)"
            )
        elif age_months < 24:
            age_label = "toddler (1y)" if lang == "en" else "طفل رضيع (سنة)"
        else:
            age_label = (
                f"child ({age_months / 12:.1f}y)"
                if lang == "en"
                else f"طفل ({age_months / 12:.1f} سنة)"
            )

        return {
            "patient_age_context": age_label,
            "age_months": age_months,
            "weight_kg": weight_kg,
            "triage_level": highest_level,
            "red_flags": red_flags_found,
            "has_red_flags": len(red_flags_found) > 0,
            "dose_assessments": dose_assessments,
            "safety_note": (
                "All dose calculations are for reference only. "
                "Confirm with a licensed prescriber before administering."
                if lang == "en"
                else "جميع حسابات الجرعة للإرشاد فقط. تأكد من طبيب مرخص قبل الإعطاء."
            ),
        }
