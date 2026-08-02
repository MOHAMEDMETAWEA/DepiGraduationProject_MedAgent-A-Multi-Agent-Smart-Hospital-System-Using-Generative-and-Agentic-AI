"""Tool: clinical_lookup — KB-grounded clinical content for the agent.

This is *the* tool that turns MedAgent from "another generic chatbot" into
a clinically-grounded triage assistant. Instead of hoping the LLM happens
to know the right red flags / OTC dose / differential for a given symptom,
we look the chief complaint up in :mod:`app.clinical` (NICE CKS + WHO IMCI
content) and hand the LLM a clean, evidence-based packet to base its reply
on.

The same packet powers two product modes:

1. **Patient triage** (B2C/B2B2C): the LLM reads it and writes an empathic
   reply for the patient (with the actual OTC name, dose, and escalation
   signs we curated).
2. **Pre-visit intake** (B2B): the doctor receives the packet rendered as
   a structured H&P sheet (HPI / red flags / differentials / proposed
   workup) — no LLM prose needed; the data IS the deliverable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool
from app.clinical.kb import get_kb


class ClinicalLookupInput(BaseModel):
    """Input schema for the clinical lookup tool.

    All fields are deliberately lenient because the LLM tool-call layer is
    untyped JSON from the model's perspective — Groq's strict validator
    will reject the *whole* call if any field is the wrong primitive type
    (e.g. ``"null"`` instead of ``null``, or ``"42"`` instead of ``42``).
    We coerce here so a slightly mis-typed call still works instead of
    exploding with ``Provider API Error: tool call validation failed``.
    """

    symptom_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description=(
            "The patient's chief complaint in their own words. Free-form "
            "text in Arabic or English. The tool will match this against "
            "the curated complaint catalogue (chest_pain, fever, headache, "
            "cough, abdominal_pain, back_pain, diarrhea, sore_throat, "
            "skin_rash, fatigue) and return the clinical packet for that "
            "complaint."
        ),
    )
    language: str = Field(
        default="ar",
        description="Output language: ar | en",
    )
    # IMPORTANT: type is intentionally `int | str | None`, not `int | None`.
    # Groq's tool-validator inspects the OpenAI function schema we publish
    # (generated from this annotation) and rejects the whole call if the
    # LLM puts a string here — which Llama-4 / Qwen routinely do when
    # they don't know the patient's age ("null" string, empty string,
    # "42" instead of 42). The field_validator below coerces every shape
    # back to int|None for us — so the LLM stays happy AND our code stays
    # safe. This is a sharp edge of running OSS models behind Groq.
    age_years: int | str | None = Field(
        default=None,
        description="Patient age in years (0-120). Used to flag age-dependent contraindications.",
    )

    @field_validator("language", mode="before")
    @classmethod
    def _normalize_language(cls, v: Any) -> str:
        """Coerce language to a safe value. The LLM sometimes sends 'arabic'
        or 'AR' or 'en-US' — we just normalize to {ar, en} and default to ar."""
        if not v or not isinstance(v, str):
            return "ar"
        v_lower = v.strip().lower()
        if v_lower.startswith("ar"):
            return "ar"
        if v_lower.startswith("en"):
            return "en"
        return "ar"

    @field_validator("age_years", mode="before")
    @classmethod
    def _coerce_age(cls, v: Any) -> int | None:
        """Coerce age_years from any shape the LLM might invent.

        Real failures we've seen from Groq/Llama:
        - ``"null"`` (string) → should be None
        - ``""`` (empty string) → should be None
        - ``"42"`` (numeric string) → should be 42
        - ``42.7`` (float) → should be 42

        We accept all of them and only reject obviously invalid ranges.
        """
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            if stripped == "" or stripped.lower() in {"null", "none", "n/a", "unknown"}:
                return None
            try:
                v = float(stripped)
            except ValueError:
                return None
        if isinstance(v, (int, float)):
            age = int(v)
            if 0 <= age <= 120:
                return age
        return None


class ClinicalLookupTool(Tool):
    """Look up a chief complaint in the clinical KB and return the packet.

    The shape of the returned dict is intentionally LLM-friendly: short
    arrays of strings the model can quote directly, plus a `_summary`
    block that the patient-facing assistant can paraphrase, and a
    `_handoff_packet` block that the doctor-facing intake mode can render
    as the H&P.
    """

    @property
    def name(self) -> str:
        return "clinical_lookup"

    @property
    def description(self) -> str:
        return (
            "Look up evidence-based clinical content for the patient's chief "
            "complaint. Returns red-flag screening questions, differential "
            "diagnoses with likelihoods, safe OTC self-care options with "
            "doses, and escalation criteria — all from curated NICE CKS / "
            "WHO IMCI content. Call this for ANY symptom-containing message; "
            "do NOT invent clinical advice without it."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return ClinicalLookupInput

    async def run(self, input_data: ClinicalLookupInput) -> dict[str, Any]:
        kb = get_kb()
        complaint = kb.find_complaint(input_data.symptom_text)
        lang = input_data.language

        if complaint is None:
            # We deliberately do NOT fall back to "see a doctor" here — that
            # was the whole anti-pattern we built this KB to escape. Instead
            # we tell the agent: "no specific guidance in KB for this one,
            # treat as a general consultation and follow the system prompt
            # rules for interim management".
            return {
                "matched": False,
                "complaint_id": None,
                "_summary": {
                    "ar": (
                        "لا يوجد بروتوكول محدد في قاعدة المعرفة لهذه الشكوى. "
                        "اتبع قواعد الاستشارة العامة وقدّم خطة interim "
                        "حسب الأعراض المذكورة."
                    ),
                    "en": (
                        "No specific KB protocol matched this complaint. "
                        "Follow general consultation rules and provide an "
                        "interim management plan based on the symptoms given."
                    ),
                }[lang],
            }

        # Pick the localized strings up-front so the engine layer doesn't
        # have to know about BilingualText.
        def t(field: Any) -> str:
            """Pick AR/EN out of a BilingualText helper."""
            if field is None:
                return ""
            return getattr(field, lang, "") or getattr(field, "en", "")

        def t_list(items: list[Any]) -> list[str]:
            return [t(i) for i in items if t(i)]

        # ── Red flags: the most important section ──────────────────
        red_flag_questions: list[dict[str, Any]] = [
            {
                "question": t(rf.question),
                "severity": rf.severity,
                "rationale": rf.rationale,
            }
            for rf in complaint.red_flags
        ]

        # ── Differentials: short list with qualitative likelihood ──
        differentials: list[dict[str, Any]] = [
            {
                "name": t(d.name),
                "likelihood": d.likelihood,
                "key_features": t_list(d.key_features),
                "icd10": d.icd10,
            }
            for d in complaint.differentials
        ]

        # ── Self-care with drug brand names + dose ─────────────────
        # We resolve the drug_id into actual formulary content so the LLM
        # gets the Egyptian brand names ("Brufen", "Cetal") inline.
        self_care: list[dict[str, Any]] = []
        for tx in complaint.self_care:
            entry: dict[str, Any] = {
                "instruction": t(tx.instruction),
                "duration": tx.duration,
                "contraindications": t_list(tx.contraindications),
                "drug_id": tx.drug_id,
            }
            if tx.drug_id:
                drug = kb.get_drug(tx.drug_id)
                if drug is not None:
                    entry["brand_names_eg"] = drug.brand_names_eg
                    entry["otc"] = drug.otc
                    entry["pediatric_min_age_years"] = drug.pediatric_min_age_years
            self_care.append(entry)

        # ── Doctor-facing handoff packet ───────────────────────────
        # The intake-mode H&P sheet shows differentials + workup +
        # red-flag rationales (clinical reasoning fields the patient
        # shouldn't see) so the doctor can confirm/override quickly.
        handoff_packet = {
            "complaint_id": complaint.id,
            "complaint_name": t(complaint.name),
            "category": complaint.category,
            "differentials": differentials,
            "red_flag_rationales": [
                {"question": t(rf.question), "rationale": rf.rationale}
                for rf in complaint.red_flags
            ],
            "proposed_workup": [
                {
                    "name": t(w.name),
                    "indication": t(w.indication),
                    "priority": w.priority,
                }
                for w in complaint.workup
            ],
            "sources": complaint.sources,
        }

        return {
            "matched": True,
            "complaint_id": complaint.id,
            "complaint_name": t(complaint.name),
            "red_flag_questions": red_flag_questions,
            "differentials": differentials,
            "followup_questions": [
                {"field_id": q.field_id, "question": t(q.question), "relevance": q.relevance}
                for q in complaint.followup_questions
            ],
            "self_care": self_care,
            "when_to_escalate": t_list(complaint.when_to_escalate),
            "sources": complaint.sources,
            "_handoff_packet": handoff_packet,
        }
