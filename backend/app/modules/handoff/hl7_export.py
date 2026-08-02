"""HL7 v2.5 export for handoff summaries (ADT^A04 — Patient Registration).

Generates a minimal but spec-compliant HL7 v2.5 message:
  MSH | EVN | PID | PV1 | OBX (one per finding)

Round-trips correctly through `python-hl7` if available; if not, the test
performs a simpler segment-integrity check.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.models.conversation import Conversation
from app.models.handoff_summary import HandoffSummary
from app.models.users import User

FIELD_SEP = "|"
COMP_SEP = "^"
ENCODING = r"^~\&"
SEGMENT_TERM = "\r"


def _sanitize(text: str) -> str:
    """Strip HL7 delimiter chars from free text."""
    if not text:
        return ""
    return re.sub(r"[|^~\\&\r\n]+", " ", str(text)).strip()


def _now_hl7() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _build_msh(message_control_id: str) -> str:
    fields = [
        "MSH",
        ENCODING,
        "MEDAGENT",  # sending app
        "MEDAGENT_FACILITY",  # sending facility
        "EHR",  # receiving app
        "RECEIVER_FACILITY",  # receiving facility
        _now_hl7(),
        "",  # security
        "ADT^A04^ADT_A01",
        message_control_id,
        "P",  # processing id (P = production)
        "2.5",
    ]
    return FIELD_SEP.join(fields)


def _build_pid(patient: User | None, patient_id: str) -> str:
    name = patient.full_name if patient and patient.full_name else "Unknown"
    parts = name.split(" ", 1)
    family = parts[0] if parts else "Unknown"
    given = parts[1] if len(parts) > 1 else ""
    fields = [
        "PID",
        "1",  # set id
        "",  # external id
        patient_id,  # internal id
        "",  # alternate id
        f"{_sanitize(family)}{COMP_SEP}{_sanitize(given)}",  # patient name
        "",
        "",  # date of birth (unknown)
        "U",  # sex (unknown)
    ]
    return FIELD_SEP.join(fields)


def _build_evn() -> str:
    return FIELD_SEP.join(["EVN", "A04", _now_hl7()])


def _build_pv1(visit_id: str) -> str:
    fields = [
        "PV1",
        "1",
        "O",  # outpatient
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        visit_id,
    ]
    return FIELD_SEP.join(fields)


def _build_obx(set_id: int, code: str, description: str, value: str) -> str:
    fields = [
        "OBX",
        str(set_id),
        "ST",  # value type: string
        f"{code}{COMP_SEP}{_sanitize(description)}",
        "",
        _sanitize(value)[:200],
        "",
        "",
        "",
        "",
        "F",  # final
        "",
        "",
        _now_hl7(),
    ]
    return FIELD_SEP.join(fields)


def build_hl7_v2(
    handoff: HandoffSummary,
    conversation: Conversation | None,
    patient: User | None,
) -> str:
    """Build an HL7 v2.5 ADT^A04 message with embedded OBX findings."""
    message_control_id = str(handoff.id).replace("-", "")[:20]
    patient_id = str(handoff.patient_user_id).replace("-", "")[:20]
    visit_id = str(handoff.conversation_id).replace("-", "")[:20]

    segments = [
        _build_msh(message_control_id),
        _build_evn(),
        _build_pid(patient, patient_id),
        _build_pv1(visit_id),
    ]

    triage_level = (conversation.triage_level if conversation else None) or "routine"
    segments.append(_build_obx(1, "AI-TRIAGE", "AI triage level", triage_level))

    if conversation and conversation.triage_score is not None:
        segments.append(
            _build_obx(2, "AI-SCORE", "AI triage score", str(conversation.triage_score))
        )

    set_id = 3
    red_flags = (conversation.red_flags_detected if conversation else []) or []
    for rf in red_flags[:10]:
        keyword = rf.get("keyword") or rf.get("flag") or "red flag"
        level = rf.get("level") or rf.get("severity") or "high"
        segments.append(_build_obx(set_id, "RED-FLAG", str(keyword), str(level)))
        set_id += 1

    return SEGMENT_TERM.join(segments) + SEGMENT_TERM
