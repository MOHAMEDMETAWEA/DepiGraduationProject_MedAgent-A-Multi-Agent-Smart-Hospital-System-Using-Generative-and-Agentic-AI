"""
T3.02 — Gold Eval Set Generator

Creates the 200-case gold evaluation set from labeled datasets.
Each case includes: chief complaint, symptoms, expected triage, language.

Cases are balanced across:
- triage levels (emergency / urgent / routine)
- languages (Arabic / English)

After generation: MANUAL REVIEW REQUIRED before use.
"""

import json
import random
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
GOLD_DIR = DATA_DIR / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

TARGET = 200
TARGETS = {
    "emergency": 50,  # 25% — underrepresented in data, but critical
    "urgent": 70,  # 35%
    "routine": 80,  # 40%
}


def load_labeled(filename: str) -> list[dict]:
    """Load labeled JSONL file."""
    path = RAW_DIR / f"labeled_{filename}"
    if not path.exists():
        print(f"  (not found: {path.name})")
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    print(f"  loaded {len(rows)} from {path.name}")
    return rows


def pick_cases(rows: list[dict], level: str, count: int) -> list[dict]:
    """Pick 'count' cases with given triage level."""
    pool = [r for r in rows if r.get("triage_level") == level]
    selected = random.sample(pool, min(count, len(pool)))
    return selected


def to_eval_format(row: dict, lang: str) -> dict:
    """Convert raw row to gold eval format."""
    return {
        "id": row.get("id", ""),
        "language": lang,
        "chief_complaint": row.get("patient", row.get("question", row.get("description", ""))),
        "symptoms": row.get("doctor", row.get("answer", "")),
        "expected_triage": row.get("triage_level", "routine"),
        "expected_score_range": [
            row.get("triage_score", 50) - 10,
            row.get("triage_score", 50) + 10,
        ],
        "source": row.get("source", "auto-labeled"),
        "verified": False,
    }


def generate_gold_set():
    """Generate the 200-case gold eval set."""
    print("Loading labeled datasets...")
    en_rows = (
        load_labeled("meddialog_en.jsonl")
        + load_labeled("healthcare_magic_en.jsonl")
        + load_labeled("medqa_en.jsonl")
    )

    if not en_rows:
        print("\nNo labeled data found. Run label_triage.py first!")
        return

    gold = []
    for level, count in TARGETS.items():
        cases = pick_cases(en_rows, level, count)
        for c in cases:
            gold.append(to_eval_format(c, "en"))
        print(f"  {level}: {len(cases)} cases")

    # Shuffle
    random.shuffle(gold)

    # Save
    output = GOLD_DIR / "triage_eval.jsonl"
    with open(output, "w", encoding="utf-8") as f:
        for case in gold:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"\nGold eval set: {len(gold)} cases → {output}")
    print("⚠️  MANUAL REVIEW REQUIRED before using for evaluation!")


if __name__ == "__main__":
    generate_gold_set()
