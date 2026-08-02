"""Typed schemas for the clinical knowledge base.

These pydantic models define the shape of every YAML file in this package.
A YAML that doesn't validate against the schema is rejected at load time —
that's the contract the rest of the agent relies on, so we can mass-author
content without worrying about typo'd field names breaking the engine.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Chief complaint decision tree ──────────────────────────────────────


class BilingualText(BaseModel):
    """Text in both languages. Most user-facing strings live here so the
    agent can pick the right one based on conversation language."""

    ar: str
    en: str


class RedFlag(BaseModel):
    """A single red-flag question to triage early in the conversation.

    If the patient answers YES to any of these, the agent escalates
    severity (default: emergency unless overridden). The list of red
    flags is the most important part of every chief complaint — it's
    what stops the system from sending an MI home with paracetamol.
    """

    question: BilingualText
    severity: str = Field(
        default="emergency",
        pattern="^(emergency|urgent)$",
        description="Severity to assign if the patient answers yes.",
    )
    rationale: str = Field(
        default="",
        description="One-line clinical rationale (for doctor handoff, not shown to patient).",
    )


class Differential(BaseModel):
    """One entry in the differential diagnosis list for this complaint."""

    name: BilingualText
    likelihood: str = Field(
        pattern="^(very_common|common|uncommon|rare|emergency)$",
        description="Qualitative likelihood — surfaced in the UI as a chip "
        "instead of a fake-precise percentage.",
    )
    key_features: list[BilingualText] = Field(default_factory=list)
    icd10: str | None = None


class TreatmentOption(BaseModel):
    """A safe self-care / OTC treatment option the agent can recommend.

    All fields are deliberately concrete (dose + frequency + max + duration)
    because the whole product point is to give the patient *something to do
    tonight*, not a "see a doctor" deflection.
    """

    drug_id: str = Field(
        description="Reference into formulary/. Empty string for "
        "non-drug measures like 'cold compress'.",
        default="",
    )
    instruction: BilingualText
    duration: str = Field(
        default="",
        description="e.g. 'until symptoms resolve', '3 days max', '48 h'",
    )
    contraindications: list[BilingualText] = Field(default_factory=list)


class WorkupItem(BaseModel):
    """A test / investigation the doctor will likely order.

    Used in the pre-visit intake mode so the doctor sees what's already
    been suggested — they can confirm or override. Not patient-facing.
    """

    name: BilingualText
    indication: BilingualText
    priority: str = Field(pattern="^(routine|urgent|emergent)$", default="routine")


class FollowupQuestion(BaseModel):
    """A clarifying question the agent should ask if not already known.

    The triage engine asks at most ``max_questions`` of these before
    committing to a triage decision — we don't want a 20-question
    interrogation, we want enough signal to be safe.
    """

    field_id: str = Field(
        description="Internal key (e.g. 'duration', 'pain_location'). "
        "Used by the intake-mode H&P template."
    )
    question: BilingualText
    relevance: str = Field(
        default="always",
        pattern="^(always|if_no_red_flag|if_urgent)$",
        description="When to ask. 'always' = baseline triage; "
        "'if_no_red_flag' = skip when we already know it's an emergency.",
    )


class ChiefComplaint(BaseModel):
    """A complete YAML entry for one chief complaint.

    Maps 1:1 to a file in ``chief_complaints/``. The whole point of the
    schema is to make the YAML files boring to write — fill in the slots,
    the engine handles routing, language, and presentation.
    """

    id: str = Field(
        description="Stable kebab-case identifier — also the YAML filename "
        "without extension. Don't rename once published.",
        pattern="^[a-z][a-z0-9_-]*$",
    )
    name: BilingualText
    synonyms: list[str] = Field(
        default_factory=list,
        description="Lowercased terms in either language that should "
        "match this complaint (e.g. 'حمى', 'fever', 'high temp', 'سخونة').",
    )
    category: str = Field(
        default="general",
        description="Free-text grouping: cardiovascular, respiratory, gi, "
        "neuro, derm, msk, gu, mental_health, general.",
    )
    age_range: str = Field(
        default="adult",
        pattern="^(neonate|infant|child|adolescent|adult|geriatric|all)$",
        description="Primary age range — separate YAML for pediatric "
        "variants of the same complaint.",
    )

    red_flags: list[RedFlag] = Field(default_factory=list)
    differentials: list[Differential] = Field(default_factory=list)
    followup_questions: list[FollowupQuestion] = Field(default_factory=list)
    self_care: list[TreatmentOption] = Field(default_factory=list)
    workup: list[WorkupItem] = Field(default_factory=list)

    when_to_escalate: list[BilingualText] = Field(
        default_factory=list,
        description="Watch-signal bullets shown to the patient: 'come back / "
        "go to ER if X, Y, Z'. These appear in the WatchSignalsCard.",
    )

    sources: list[str] = Field(
        default_factory=list,
        description="URLs / citations (NICE CKS, WHO IMCI). One per source.",
    )

    needs_clinical_review: bool = Field(
        default=True,
        description="Flag content that hasn't been signed off by a "
        "licensed physician yet. We default true so unreviewed content "
        "is visible in audits.",
    )


# ── Drug formulary ─────────────────────────────────────────────────────


class DoseRule(BaseModel):
    """One row in a per-age / per-weight dosing table.

    Pediatric dosing in particular is always weight-based — we cannot
    safely tell a parent "give 5 ml" without the kid's weight.
    """

    min_age_years: float | None = None
    max_age_years: float | None = None
    weight_based: bool = Field(
        default=False,
        description="True for pediatric weight-based dosing (mg/kg).",
    )
    dose: str = Field(
        description="Free-text dose: '500-1000 mg PO every 6 h' or "
        "'15 mg/kg every 6 h, max 75 mg/kg/day'.",
    )
    max_daily: str | None = None
    notes: BilingualText | None = None


class Drug(BaseModel):
    """One entry in the formulary."""

    id: str = Field(pattern="^[a-z][a-z0-9_-]*$")
    generic_name: BilingualText
    brand_names_eg: list[str] = Field(
        default_factory=list,
        description="Common Egyptian brand names (Cetal, Panadol, "
        "Brufen, Augmentin, …) so patients recognise what's on shelf.",
    )
    drug_class: str = Field(default="other")
    otc: bool = Field(
        default=False,
        description="True if available without prescription in Egypt. "
        "We never recommend a non-OTC drug as a self-care measure.",
    )

    dosing: list[DoseRule] = Field(default_factory=list)
    indications: list[BilingualText] = Field(default_factory=list)
    contraindications: list[BilingualText] = Field(default_factory=list)
    common_interactions: list[BilingualText] = Field(default_factory=list)

    pregnancy_category: str | None = Field(
        default=None,
        description="FDA letter A/B/C/D/X (legacy but widely understood) or 'avoid', 'unknown'.",
    )
    pediatric_min_age_years: float | None = Field(
        default=None,
        description="Hard floor — never recommend under this age. None = "
        "no specific lower bound documented.",
    )

    sources: list[str] = Field(default_factory=list)


# ── Specialty intake templates ─────────────────────────────────────────


class IntakeField(BaseModel):
    """One field on the H&P sheet the doctor will receive."""

    id: str
    label: BilingualText
    section: str = Field(
        pattern="^(demographics|chief_complaint|hpi|pmh|meds|allergies|"
        "social|family|ros|vitals|exam|differential)$",
        description="Which section of the H&P this field populates.",
    )
    required: bool = Field(default=False)
    free_text: bool = Field(default=True)


class SpecialtyTemplate(BaseModel):
    """Pre-visit intake template for one specialty."""

    id: str = Field(pattern="^[a-z][a-z0-9_-]*$")
    name: BilingualText
    description: BilingualText
    fields: list[IntakeField] = Field(default_factory=list)
    required_red_flag_complaints: list[str] = Field(
        default_factory=list,
        description="Chief-complaint IDs that this specialty must always "
        "screen for red flags on (e.g. cardiology → always ask chest pain).",
    )
