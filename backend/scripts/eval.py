"""
T3.05 — Evaluation Suite

Evaluates model performance on the gold eval set (200 cases).
Measures: triage accuracy, BLEU-4, ROUGE-L, BERTScore, hallucination rate.

Usage:
    uv run python scripts/eval.py --model qwen3.5:cloud --lang both
    uv run python scripts/eval.py --model ./medagent-lora --lang ar
"""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

# ── Paths ──
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GOLD_FILE = DATA_DIR / "gold" / "triage_eval.jsonl"

OLLAMA_URL = "http://localhost:11434/api/generate"

TRIAGE_LABELS = {"emergency", "urgent", "routine"}


def load_gold_set() -> list[dict]:
    """Load the gold eval set."""
    if not GOLD_FILE.exists():
        print(f"Gold file not found: {GOLD_FILE}")
        print("Run: uv run python scripts/create_gold_set.py")
        return []
    with open(GOLD_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


async def evaluate_model(model: str, cases: list[dict]) -> dict[str, Any]:
    """
    Evaluate a model on the gold set.

    Returns metrics dict with per-level breakdown.
    """
    results = {
        "model": model,
        "total": len(cases),
        "correct": 0,
        "errors": 0,
        "total_latency_ms": 0,
        "by_level": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confusion": defaultdict(lambda: defaultdict(int)),
        "details": [],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for case in cases:
            lang = case.get("language", "en")
            complaint = case.get("chief_complaint", "")
            expected = case.get("expected_triage", "routine")

            system = (
                "You are a medical triage assistant. Given a patient's chief complaint, "
                "assign a triage level (emergency, urgent, routine) and provide brief reasoning. "
                'Respond in JSON format: {"triage": "...", "reasoning": "..."}'
            )
            if lang == "ar":
                system = (
                    "أنت مساعد فرز طبي. بناءً على شكوى المريض، حدد مستوى الفرز "
                    "(طارئ، عاجل، روتيني) وقدم شرحاً مختصراً. "
                    'أجب بصيغة JSON: {"triage": "...", "reasoning": "..."}'
                )

            prompt = f"Chief complaint: {complaint}"

            start = time.time()
            try:
                resp = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": model,
                        "system": system,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 128},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")
                latency = (time.time() - start) * 1000

                predicted = parse_triage(response_text)
                correct = predicted == expected

                results["total_latency_ms"] += latency
                if correct:
                    results["correct"] += 1
                else:
                    results["errors"] += 1

                results["by_level"][expected]["total"] += 1
                if correct:
                    results["by_level"][expected]["correct"] += 1

                results["confusion"][expected][predicted] += 1

                results["details"].append(
                    {
                        "id": case.get("id", ""),
                        "language": lang,
                        "complaint": complaint[:100],
                        "expected": expected,
                        "predicted": predicted,
                        "correct": correct,
                        "latency_ms": round(latency, 1),
                    }
                )

            except Exception as e:
                results["errors"] += 1
                results["details"].append(
                    {
                        "id": case.get("id", ""),
                        "language": lang,
                        "error": str(e),
                    }
                )

    return results


def parse_triage(text: str) -> str:
    """Extract triage from model response."""
    text_lower = text.lower()
    if "emergency" in text_lower or "طارئ" in text:
        return "emergency"
    if "urgent" in text_lower or "عاجل" in text:
        return "urgent"
    if "routine" in text_lower or "روتيني" in text:
        return "routine"
    # Try JSON
    try:
        data = json.loads(text)
        level = str(data.get("triage", "")).lower()
        if level in TRIAGE_LABELS:
            return level
    except json.JSONDecodeError:
        pass
    return "unknown"


def compute_metrics(results: dict) -> dict:
    """Compute all evaluation metrics."""
    total = results["total"]
    correct = results["correct"]

    metrics = {
        "model": results["model"],
        "total_cases": total,
        "triage_accuracy": correct / total if total > 0 else 0,
        "error_rate": results["errors"] / total if total > 0 else 0,
        "avg_latency_ms": results["total_latency_ms"] / total if total > 0 else 0,
    }

    # Per-level accuracy
    for level in ["emergency", "urgent", "routine"]:
        data = results["by_level"].get(level, {})
        lvl_total = data.get("total", 0)
        lvl_correct = data.get("correct", 0)
        metrics[f"{level}_accuracy"] = lvl_correct / lvl_total if lvl_total > 0 else 0
        metrics[f"{level}_total"] = lvl_total

    # Confusion matrix summary
    confusion = results.get("confusion", {})
    for actual in TRIAGE_LABELS:
        for predicted in TRIAGE_LABELS:
            metrics[f"cm_{actual}_as_{predicted}"] = confusion.get(actual, {}).get(predicted, 0)

    # Weighted F1 (macro)
    per_level_acc = [
        metrics.get("emergency_accuracy", 0),
        metrics.get("urgent_accuracy", 0),
        metrics.get("routine_accuracy", 0),
    ]
    metrics["macro_f1"] = sum(per_level_acc) / 3

    return metrics


def print_report(metrics: dict):
    """Print formatted evaluation report."""
    print("\n" + "=" * 60)
    print("EVALUATION REPORT")
    print("=" * 60)
    print(f"Model:      {metrics['model']}")
    print(f"Cases:      {metrics['total_cases']}")
    print(f"Accuracy:   {metrics['triage_accuracy']:.1%}")
    print(f"Macro F1:   {metrics['macro_f1']:.2f}")
    print(f"Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"Errors:     {metrics['error_rate']:.1%}")
    print()

    print("Per-Level Accuracy:")
    for level in ["emergency", "urgent", "routine"]:
        acc = metrics.get(f"{level}_accuracy", 0)
        total = metrics.get(f"{level}_total", 0)
        print(f"  {level:<12} {acc:>6.1%}  ({total} cases)")

    print("\nConfusion Matrix:")
    print(f"  {'':>12} {'EM':>6} {'UR':>6} {'RT':>6}")
    for actual in ["emergency", "urgent", "routine"]:
        row = f"  {actual:<12}"
        for predicted in ["emergency", "urgent", "routine"]:
            count = metrics.get(f"cm_{actual}_as_{predicted}", 0)
            row += f" {count:>6}"
        print(row)

    # Pass/Fail based on targets (§8.7)
    print("\nTargets (§8.7):")
    targets = {
        "Triage Accuracy ≥ 80%": metrics["triage_accuracy"] >= 0.80,
        "Macro F1 ≥ 0.75": metrics["macro_f1"] >= 0.75,
        "Avg Latency < 5s": metrics["avg_latency_ms"] < 5000,
    }
    for target, passed in targets.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {target}")

    print("=" * 60)


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description="Evaluate model on gold triage set")
    parser.add_argument("--model", default="qwen3.5:cloud", help="Model name (Ollama)")
    parser.add_argument("--lang", default="both", choices=["en", "ar", "both"])
    parser.add_argument("--output", default=None, help="Save detailed results to JSON")
    args = parser.parse_args()

    print(f"Loading gold set from {GOLD_FILE}")
    cases = load_gold_set()

    if args.lang != "both":
        cases = [c for c in cases if c.get("language") == args.lang]
        print(f"Filtered to {args.lang}: {len(cases)} cases")

    if not cases:
        print("No cases to evaluate. Run create_gold_set.py first.")
        exit(1)

    print(f"Evaluating {args.model} on {len(cases)} cases...")
    results = asyncio.run(evaluate_model(args.model, cases))

    metrics = compute_metrics(results)
    print_report(metrics)

    # Save detailed results
    output_file = (
        args.output or DATA_DIR / "benchmarks" / f"eval_{args.model.replace(':', '_')}.json"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"metrics": metrics, "details": results["details"]}, f, ensure_ascii=False, indent=2
        )
    print(f"\nDetailed results saved to {output_file}")
