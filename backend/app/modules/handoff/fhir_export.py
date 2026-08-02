"""FHIR R4 Bundle export for handoff summaries.

Generates a `Bundle` (type=document) where the first entry is a `Composition`
linking to Patient, Condition, Observation, ClinicalImpression resources
derived from the handoff summary + parent conversation.

The generated structure passes the public HAPI FHIR validator for
Bundle.type=document. We avoid external `fhir.resources` to keep the
dep surface small — JSON shape is hand-built per HL7 R4 spec.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.conversation import Conversation
from app.models.handoff_summary import HandoffSummary
from app.models.users import User

FHIR_VERSION = "4.0.1"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _new_uuid_urn() -> str:
    return f"urn:uuid:{uuid.uuid4()}"


def _coding(system: str, code: str, display: str) -> dict:
    return {"system": system, "code": code, "display": display}


def _codeable(text: str, codings: list[dict] | None = None) -> dict:
    out: dict = {"text": text}
    if codings:
        out["coding"] = codings
    return out


def _extract_section(markdown: str, header_aliases: list[str]) -> str:
    """Extract a single markdown section's body by matching any of the given headers (case-insensitive)."""
    if not markdown:
        return ""
    pattern = re.compile(
        r"^#{1,4}\s*(?:" + "|".join(re.escape(h) for h in header_aliases) + r")\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    start = match.end()
    next_header = re.search(r"^#{1,4}\s+\S", markdown[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(markdown)
    return markdown[start:end].strip()


def _bullets(section_body: str) -> list[str]:
    """Parse markdown bullet list into plain strings."""
    out = []
    for line in section_body.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            out.append(line.lstrip("-*•").strip())
        elif line and not line.startswith("#"):
            out.append(line)
    return out


def build_fhir_bundle(
    handoff: HandoffSummary,
    conversation: Conversation | None,
    patient: User | None,
) -> dict[str, Any]:
    """Build a FHIR R4 Bundle (type=document) from a handoff summary.

    Returns a JSON-serializable dict ready to ship as ``application/fhir+json``.
    """
    md = handoff.summary_markdown or ""
    bundle_id = str(handoff.id)
    composition_urn = _new_uuid_urn()
    patient_urn = _new_uuid_urn()

    # ── Patient ──
    patient_resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_urn.split(":")[-1],
        "active": True,
    }
    if patient is not None:
        patient_resource["name"] = [{"text": patient.full_name or "Patient", "use": "official"}]
        if patient.email:
            patient_resource["telecom"] = [
                {"system": "email", "value": patient.email, "use": "home"}
            ]

    # ── Condition (chief complaint / symptoms) ──
    condition_text = _extract_section(
        md, ["Chief Complaint", "الشكوى الرئيسية", "Symptoms", "الأعراض"]
    )
    condition_urn = _new_uuid_urn()
    condition_resource = {
        "resourceType": "Condition",
        "id": condition_urn.split(":")[-1],
        "subject": {"reference": patient_urn},
        "code": _codeable(condition_text or "Patient-reported symptoms"),
        "clinicalStatus": _codeable(
            "active",
            [
                _coding(
                    "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "active",
                    "Active",
                )
            ],
        ),
        "verificationStatus": _codeable(
            "unconfirmed",
            [
                _coding(
                    "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "unconfirmed",
                    "Unconfirmed",
                )
            ],
        ),
        "recordedDate": _now_iso(),
    }

    # ── Observations (red flags + AI triage) ──
    observation_entries: list[dict[str, Any]] = []
    triage_level = (conversation.triage_level if conversation else None) or "routine"
    triage_score = conversation.triage_score if conversation else None

    triage_obs_urn = _new_uuid_urn()
    triage_obs = {
        "resourceType": "Observation",
        "id": triage_obs_urn.split(":")[-1],
        "status": "preliminary",
        "category": [
            _codeable(
                "AI Triage Assessment",
                [
                    _coding(
                        "http://terminology.hl7.org/CodeSystem/observation-category",
                        "survey",
                        "Survey",
                    )
                ],
            )
        ],
        "code": _codeable(
            "AI triage level",
            [_coding("http://medagent.local/codes", "ai-triage-level", "AI Triage Level")],
        ),
        "subject": {"reference": patient_urn},
        "effectiveDateTime": _now_iso(),
        "valueCodeableConcept": _codeable(triage_level),
        "component": (
            [
                {
                    "code": _codeable(
                        "Triage score",
                        [
                            _coding(
                                "http://medagent.local/codes",
                                "ai-triage-score",
                                "AI Triage Score",
                            )
                        ],
                    ),
                    "valueQuantity": {"value": triage_score, "unit": "score"},
                }
            ]
            if triage_score is not None
            else []
        ),
    }
    observation_entries.append({"urn": triage_obs_urn, "resource": triage_obs})

    # Red flags as observations
    red_flags = (conversation.red_flags_detected if conversation else []) or []
    for rf in red_flags[:10]:
        rf_urn = _new_uuid_urn()
        keyword = rf.get("keyword") or rf.get("flag") or "red flag"
        level = rf.get("level") or rf.get("severity") or "high"
        rf_obs = {
            "resourceType": "Observation",
            "id": rf_urn.split(":")[-1],
            "status": "preliminary",
            "category": [
                _codeable(
                    "Clinical red flag",
                    [
                        _coding(
                            "http://terminology.hl7.org/CodeSystem/observation-category",
                            "exam",
                            "Exam",
                        )
                    ],
                )
            ],
            "code": _codeable(f"Red flag: {keyword}"),
            "subject": {"reference": patient_urn},
            "effectiveDateTime": _now_iso(),
            "valueString": str(level),
        }
        observation_entries.append({"urn": rf_urn, "resource": rf_obs})

    # ── ClinicalImpression (AI-generated assessment) ──
    impression_text = _extract_section(
        md, ["AI Triage", "Recommended Next Steps", "التقييم", "الخطة"]
    )
    impression_urn = _new_uuid_urn()
    impression_resource = {
        "resourceType": "ClinicalImpression",
        "id": impression_urn.split(":")[-1],
        "status": "in-progress",
        "subject": {"reference": patient_urn},
        "date": _now_iso(),
        "summary": (impression_text or "AI-generated triage assessment.")[:5000],
        "note": [{"text": "Generated by MedAgent AI — preliminary, not a diagnosis."}],
    }

    # ── Composition (table of contents for the Bundle) ──
    sections = [
        {
            "title": "Chief Complaint",
            "code": _codeable(
                "Chief complaint",
                [_coding("http://loinc.org", "10154-3", "Chief complaint")],
            ),
            "entry": [{"reference": condition_urn}],
        },
        {
            "title": "Findings & Red Flags",
            "code": _codeable(
                "Relevant findings",
                [_coding("http://loinc.org", "8716-3", "Vital signs")],
            ),
            "entry": [{"reference": e["urn"]} for e in observation_entries],
        },
        {
            "title": "AI Assessment & Plan",
            "code": _codeable(
                "Plan of care",
                [_coding("http://loinc.org", "18776-5", "Plan of care note")],
            ),
            "entry": [{"reference": impression_urn}],
        },
    ]

    composition_resource = {
        "resourceType": "Composition",
        "id": composition_urn.split(":")[-1],
        "status": "preliminary",
        "type": _codeable(
            "Triage handoff summary",
            [_coding("http://loinc.org", "11488-4", "Consult note")],
        ),
        "subject": {"reference": patient_urn},
        "date": _now_iso(),
        "author": [{"display": "MedAgent AI", "reference": "Device/medagent-ai"}],
        "title": "MedAgent Triage Handoff Summary",
        "section": sections,
    }

    # ── Bundle ──
    entries: list[dict[str, Any]] = [
        {"fullUrl": composition_urn, "resource": composition_resource},
        {"fullUrl": patient_urn, "resource": patient_resource},
        {"fullUrl": condition_urn, "resource": condition_resource},
    ]
    for obs in observation_entries:
        entries.append({"fullUrl": obs["urn"], "resource": obs["resource"]})
    entries.append({"fullUrl": impression_urn, "resource": impression_resource})

    bundle: dict[str, Any] = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "document",
        "timestamp": _now_iso(),
        "entry": entries,
        "meta": {
            "lastUpdated": _now_iso(),
            "profile": [f"http://hl7.org/fhir/StructureDefinition/Bundle|{FHIR_VERSION}"],
        },
    }
    return bundle


def serialize_bundle(bundle: dict[str, Any]) -> str:
    """JSON-encode a FHIR Bundle for transport."""
    return json.dumps(bundle, ensure_ascii=False, indent=2)
