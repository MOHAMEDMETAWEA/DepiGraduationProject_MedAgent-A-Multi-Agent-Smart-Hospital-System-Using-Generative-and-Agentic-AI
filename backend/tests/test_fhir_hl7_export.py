"""T4.14 / T4.15 — FHIR + HL7 export unit tests."""

import json
import uuid

from app.modules.handoff.fhir_export import build_fhir_bundle, serialize_bundle
from app.modules.handoff.hl7_export import build_hl7_v2


class _FakeHandoff:
    def __init__(self):
        self.id = uuid.uuid4()
        self.conversation_id = uuid.uuid4()
        self.patient_user_id = uuid.uuid4()
        self.summary_markdown = (
            "## Chief Complaint\nFever and cough for 3 days.\n\n"
            "## Symptoms\n- Fever 38.5°C\n- Productive cough\n\n"
            "## AI Triage\nRoutine — likely viral upper respiratory infection.\n\n"
            "## Recommended Next Steps\nRest, fluids, paracetamol PRN.\n"
        )


class _FakeConv:
    def __init__(self, level="urgent", score=65):
        self.triage_level = level
        self.triage_score = score
        self.red_flags_detected = [
            {"keyword": "high fever", "level": "moderate"},
            {"keyword": "shortness of breath", "level": "high"},
        ]


class _FakePatient:
    def __init__(self):
        self.full_name = "Mona Ali"
        self.email = "mona@example.com"


# ─────────────────────────────────────────────
# FHIR
# ─────────────────────────────────────────────


def test_fhir_bundle_basic_structure():
    bundle = build_fhir_bundle(_FakeHandoff(), _FakeConv(), _FakePatient())
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert "timestamp" in bundle
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert types[0] == "Composition"
    assert "Patient" in types
    assert "Condition" in types
    assert "Observation" in types
    assert "ClinicalImpression" in types


def test_fhir_bundle_composition_links_all_sections():
    bundle = build_fhir_bundle(_FakeHandoff(), _FakeConv(), _FakePatient())
    composition = bundle["entry"][0]["resource"]
    section_titles = {s["title"] for s in composition["section"]}
    assert section_titles == {
        "Chief Complaint",
        "Findings & Red Flags",
        "AI Assessment & Plan",
    }


def test_fhir_bundle_serializes_to_valid_json():
    bundle = build_fhir_bundle(_FakeHandoff(), _FakeConv(), _FakePatient())
    body = serialize_bundle(bundle)
    parsed = json.loads(body)
    assert parsed["resourceType"] == "Bundle"


def test_fhir_bundle_handles_missing_patient_and_conv():
    bundle = build_fhir_bundle(_FakeHandoff(), None, None)
    assert bundle["resourceType"] == "Bundle"
    # Triage observation must still exist with default 'routine'
    obs = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"]
    assert any(o["valueCodeableConcept"]["text"] == "routine" for o in obs)


def test_fhir_bundle_red_flags_become_observations():
    bundle = build_fhir_bundle(_FakeHandoff(), _FakeConv(), _FakePatient())
    obs = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"]
    rf_codes = [o["code"]["text"] for o in obs if "Red flag" in o["code"]["text"]]
    assert len(rf_codes) == 2


# ─────────────────────────────────────────────
# HL7 v2
# ─────────────────────────────────────────────


def test_hl7_message_starts_with_msh():
    msg = build_hl7_v2(_FakeHandoff(), _FakeConv(), _FakePatient())
    segments = msg.strip().split("\r")
    assert segments[0].startswith("MSH|")
    assert "ADT^A04" in segments[0]


def test_hl7_message_has_required_segments():
    msg = build_hl7_v2(_FakeHandoff(), _FakeConv(), _FakePatient())
    segments = [s.split("|")[0] for s in msg.strip().split("\r")]
    assert "MSH" in segments
    assert "EVN" in segments
    assert "PID" in segments
    assert "PV1" in segments
    assert "OBX" in segments


def test_hl7_obx_includes_red_flags():
    msg = build_hl7_v2(_FakeHandoff(), _FakeConv(), _FakePatient())
    obx_segments = [s for s in msg.strip().split("\r") if s.startswith("OBX")]
    # 1 triage level + 1 score + 2 red flags
    assert len(obx_segments) >= 3
    assert any("AI-TRIAGE" in s for s in obx_segments)
    assert any("RED-FLAG" in s for s in obx_segments)


def test_hl7_handles_no_conv():
    msg = build_hl7_v2(_FakeHandoff(), None, _FakePatient())
    obx_segments = [s for s in msg.strip().split("\r") if s.startswith("OBX")]
    # default: AI-TRIAGE = routine
    assert any("AI-TRIAGE" in s and "routine" in s for s in obx_segments)


def test_hl7_pid_strips_delimiters_from_name():
    handoff = _FakeHandoff()
    p = _FakePatient()
    p.full_name = "Bad|Name^With~Delim"
    msg = build_hl7_v2(handoff, _FakeConv(), p)
    pid = next(s for s in msg.split("\r") if s.startswith("PID"))
    # Delimiter chars must be sanitized out of the patient name field
    name_field = pid.split("|")[5]
    assert "|" not in name_field
    assert "~" not in name_field


def test_hl7_message_terminates_with_cr():
    msg = build_hl7_v2(_FakeHandoff(), _FakeConv(), _FakePatient())
    assert msg.endswith("\r")
