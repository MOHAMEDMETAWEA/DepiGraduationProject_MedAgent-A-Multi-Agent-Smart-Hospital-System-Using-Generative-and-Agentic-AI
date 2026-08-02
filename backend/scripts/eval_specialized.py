"""
T3.11 — Specialized Tools Evaluator

Runs all specialized tool evaluations:
- Medication interactions: 20 known pairs (precision/recall)
- Mental health: PHQ-9/GAD-7 scoring accuracy
- Pediatric: 15 cases (emergency recall)
- Pregnancy: 15 cases (drug category warnings)

Usage:
    uv run python scripts/eval_specialized.py
"""

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent / "tests" / "eval" / "specialized_tools"


def eval_medication():
    """Evaluate medication interaction checker."""
    from app.ai.tools.medication import MedicationChecker

    cases = load_jsonl(EVAL_DIR / "medication.jsonl")
    if not cases:
        return {"error": "No medication eval cases"}

    checker = MedicationChecker()
    correct = 0
    total = 0

    for case in cases:
        med_a = case["med_a"]
        med_b = case["med_b"]
        expected_severity = case["interaction_severity"]

        result = checker.check_interaction(med_a, med_b)

        # Check if we detected the expected severity
        if result.get("severity") == expected_severity or (
            expected_severity == "major" and result.get("severity") in ("major", "contraindicated")
        ):
            correct += 1

        total += 1

    precision = correct / total if total > 0 else 0
    print(f"  Medication: {correct}/{total} correct ({precision:.1%})")
    return {"total": total, "correct": correct, "precision": precision}


def eval_mental_health():
    """Evaluate PHQ-9/GAD-7 scoring."""
    from app.ai.tools.mental_health import MentalHealthScreener

    cases = load_jsonl(EVAL_DIR / "mental_health.jsonl")
    if not cases:
        return {"error": "No mental health eval cases"}

    screener = MentalHealthScreener()
    correct = 0
    suidality_escalated = 0
    suidality_total = 0
    total = 0

    for case in cases:
        scale = case["scale"]
        responses = case["responses"]
        expected_severity = case["expected_severity"]

        result = screener.score(scale, responses)
        severity = result.get("severity", "")

        if severity == expected_severity:
            correct += 1

        # Check suicidality escalation
        if scale == "phq9" and len(responses) >= 9:
            suidality_total += 1
            if responses[8] > 0 and result.get("crisis"):
                suidality_escalated += 1

        total += 1

    precision = correct / total if total > 0 else 0
    suicide_recall = suidality_escalated / suidality_total if suidality_total > 0 else 1
    print(
        f"  Mental Health: {correct}/{total} correct ({precision:.1%}), suicidality recall: {suicide_recall:.1%}"
    )
    return {
        "total": total,
        "correct": correct,
        "precision": precision,
        "suicidality_recall": suicide_recall,
    }


def eval_pediatric():
    """Evaluate pediatric safety branch."""
    from app.ai.tools.assess_pediatric_safety import assess_pediatric_safety

    cases = load_jsonl(EVAL_DIR / "pediatric.jsonl")
    if not cases:
        return {"error": "No pediatric eval cases"}

    correct = 0
    emergency_correct = 0
    emergency_total = 0
    total = 0

    for case in cases:
        age_months = case["age_months"]
        symptoms = case["symptoms"]
        expected = case["expected_level"]

        level, _warnings = assess_pediatric_safety(age_months, symptoms)

        if level == expected:
            correct += 1

        if expected == "emergency":
            emergency_total += 1
            if level == "emergency":
                emergency_correct += 1

        total += 1

    precision = correct / total if total > 0 else 0
    emergency_recall = emergency_correct / emergency_total if emergency_total > 0 else 1
    print(
        f"  Pediatric: {correct}/{total} correct ({precision:.1%}), emergency recall: {emergency_recall:.1%}"
    )
    return {
        "total": total,
        "correct": correct,
        "precision": precision,
        "emergency_recall": emergency_recall,
    }


def eval_pregnancy():
    """Evaluate pregnancy safety branch."""
    from app.ai.tools.assess_pregnancy_safety import assess_pregnancy_safety

    cases = load_jsonl(EVAL_DIR / "pregnancy.jsonl")
    if not cases:
        return {"error": "No pregnancy eval cases"}

    correct = 0
    drug_warn_correct = 0
    drug_warn_total = 0
    total = 0

    for case in cases:
        week = case.get("gestational_week")
        symptoms = case["symptoms"]
        meds = case.get("meds", [])
        expected_keyword = case["expected"].lower()

        _level, warnings = assess_pregnancy_safety(week, symptoms, meds)

        # Check if warning contains expected keyword
        if (
            warnings
            and expected_keyword
            and any(kw in warnings.lower() for kw in expected_keyword.split(","))
        ):
            correct += 1

        # Check drug category warnings
        if meds:
            drug_warn_total += 1
            if warnings and any(m.lower() in warnings.lower() for m in meds):
                drug_warn_correct += 1

        total += 1

    precision = correct / total if total > 0 else 0
    drug_recall = drug_warn_correct / drug_warn_total if drug_warn_total > 0 else 1
    print(
        f"  Pregnancy: {correct}/{total} correct ({precision:.1%}), drug warning recall: {drug_recall:.1%}"
    )
    return {
        "total": total,
        "correct": correct,
        "precision": precision,
        "drug_warning_recall": drug_recall,
    }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


if __name__ == "__main__":
    print("=" * 50)
    print("T3.11 — Specialized Tools Evaluation")
    print("=" * 50)

    results = {
        "medication": eval_medication(),
        "mental_health": eval_mental_health(),
        "pediatric": eval_pediatric(),
        "pregnancy": eval_pregnancy(),
    }

    # Save report
    output = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "benchmarks"
        / "specialized_tools_report.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to {output}")
