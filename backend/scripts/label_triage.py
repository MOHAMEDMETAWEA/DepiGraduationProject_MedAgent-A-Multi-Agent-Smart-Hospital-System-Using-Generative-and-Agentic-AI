"""
T3.02 — Triage Labeler (Rule-Based)

Auto-labels triage level from chief complaint keywords.
Used to bootstrap the gold eval set — manual review required after.

Rules are based on Manchester Triage Scale priorities.
"""

import json
import re
from pathlib import Path

EMERGENCY_PATTERNS = [
    r"\bchest pain\b.*\bradiating\b",
    r"\bnot breathing\b",
    r"\bstroke\b",
    r"\bseizure\b",
    r"\bunconscious\b",
    r"\boverdose\b",
    r"\bsuicidal\b",
    r"\banaphyla\w+\b",
    r"\bsevere bleeding\b",
    r"\bchoking\b",
    r"\bcannot breathe\b",
    r"\bheart attack\b",
    r"\bpoison\b",
    r"\bcoughing blood\b",
    r"\bsudden vision loss\b",
    r"\bsudden severe\b.*\bpain\b",
    r"\bhead injury\b.*\bunconscious\b",
]

URGENT_PATTERNS = [
    r"\bhigh fever\b",
    r"\bpersistent vomiting\b",
    r"\bsevere pain\b",
    r"\bdifficulty breathing\b",
    r"\bchest pain\b",
    r"\bblood in\b",
    r"\bswelling\b.*\bsevere\b",
    r"\bfracture\b",
    r"\bburn\b",
    r"\bfainting\b",
    r"\bconfusion\b",
    r"\bdehydration\b",
    r"\binfection\b.*\bworsening\b",
    r"\bpregnant\b.*\bbleeding\b",
    r"\bbaby\b.*\bfever\b",
]

ROUTINE_PATTERNS = [
    r"\bcold\b",
    r"\bcough\b",
    r"\bsore throat\b",
    r"\brunny nose\b",
    r"\bheadache\b",
    r"\bfatigue\b",
    r"\brash\b",
    r"\bconstipation\b",
    r"\ballergy\b",
    r"\binsomnia\b",
    r"\bstress\b",
    r"\bback pain\b",
    r"\bjoint pain\b",
    r"\bcheckup\b",
    r"\bprescription\b.*\brefill\b",
]


def label_triage(text: str) -> dict:
    """
    Label triage level from text using keyword/pattern matching.

    Priority: emergency > urgent > routine > unknown
    """
    text_lower = text.lower()

    # Check emergency first (highest priority)
    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, text_lower):
            return {"level": "emergency", "score": 90, "reason": f"matched: {pattern}"}

    # Check urgent
    for pattern in URGENT_PATTERNS:
        if re.search(pattern, text_lower):
            return {"level": "urgent", "score": 70, "reason": f"matched: {pattern}"}

    # Check routine
    for pattern in ROUTINE_PATTERNS:
        if re.search(pattern, text_lower):
            return {"level": "routine", "score": 30, "reason": f"matched: {pattern}"}

    return {"level": "routine", "score": 20, "reason": "no pattern matched — default routine"}


def label_file(input_path: Path, output_path: Path):
    """Label all rows in a JSONL file."""
    with (
        open(input_path, encoding="utf-8") as fin,
        open(output_path, "w", encoding="utf-8") as fout,
    ):
        for line in fin:
            row = json.loads(line)
            # Extract text to label
            text = row.get("patient", row.get("question", row.get("description", "")))
            triage = label_triage(text)
            row["triage_level"] = triage["level"]
            row["triage_score"] = triage["score"]
            row["triage_reason"] = triage["reason"]
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Labeled {input_path.name} → {output_path.name}")


if __name__ == "__main__":
    raw = Path(__file__).resolve().parent.parent / "data" / "raw"

    for name in ["meddialog_en.jsonl", "healthcare_magic_en.jsonl", "medqa_en.jsonl"]:
        f = raw / name
        if f.exists():
            label_file(f, raw / f"labeled_{name}")
