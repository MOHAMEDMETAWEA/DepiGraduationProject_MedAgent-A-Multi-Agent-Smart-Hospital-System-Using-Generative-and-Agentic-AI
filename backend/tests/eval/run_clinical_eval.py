"""
Evaluation script for clinical test cases.
Runs each case through MedAgent and compares actual triage/flags with expected results.

Usage:
    cd backend
    uv run python tests/eval/run_clinical_eval.py
    uv run python tests/eval/run_clinical_eval.py --model groq/qwen/qwen3-32b
    uv run python tests/eval/run_clinical_eval.py --model groq/meta-llama/llama-4-scout-17b-16e-instruct
    uv run python tests/eval/run_clinical_eval.py --model oa/gpt-4o
    uv run python tests/eval/run_clinical_eval.py --case EM-001
    uv run python tests/eval/run_clinical_eval.py --category cardiac
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure backend root is in PYTHONPATH
_backend_root = Path(__file__).resolve().parents[2]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# Load .env file (needed when running outside Docker)
_dotenv_path = _backend_root / ".env"
if _dotenv_path.exists():
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                # Remove quotes
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val

CASES_FILE = Path(__file__).resolve().parent / "clinical_cases.jsonl"


def load_cases() -> list[dict]:
    cases = []
    with open(CASES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


async def run_case(case: dict, model: str, verbose: bool = True) -> dict:
    """Run a single test case through the agent and return results."""
    os.environ["DISABLE_RATE_LIMIT"] = "true"

    from app.modules.conversations.chat import _build_agent, _create_llm

    # Use the same LLM factory from chat.py (handles provider prefixes)
    llm = _create_llm(model_override=model)
    agent = _build_agent(llm)

    message = case["message"]
    language = case["language"]

    events: list[dict] = []
    full_response = ""

    try:
        async for event in agent.run(
            user_message=message,
            language=language,
        ):
            events.append(event)
            if event.type == "token":
                full_response += event.content
    except Exception as e:
        return {
            "case_id": case["id"],
            "category": case.get("category", ""),
            "language": case["language"],
            "message": case["message"][:80],
            "status": "error",
            "error": str(e),
            "expected_triage": case.get("expected_triage"),
            "actual_triage": None,
            "actual_score": None,
            "triage_match": None,
            "expected_flags": case.get("expected_flags", []),
            "red_flag_detected": False,
            "response": "",
            "tool_count": 0,
            "thinking": False,
        }

    # Extract results
    triage_event = next((e for e in events if e.type == "triage"), None)
    red_flag_event = next((e for e in events if e.type == "red_flag"), None)

    actual_triage = (
        triage_event.data.get("level")
        if triage_event
        else ("emergency" if red_flag_event else None)
    )
    actual_score = (
        triage_event.data.get("score") if triage_event else (100 if red_flag_event else None)
    )

    # Determine result
    expected_triage = case.get("expected_triage")
    triage_match = actual_triage == expected_triage if expected_triage else None

    expected_flags = case.get("expected_flags", [])
    red_flag_detected = red_flag_event is not None

    result = {
        "case_id": case["id"],
        "category": case.get("category", ""),
        "language": language,
        "message": message[:80],
        "status": "pass"
        if (triage_match and (not expected_flags or red_flag_detected))
        else "review",
        "expected_triage": expected_triage,
        "actual_triage": actual_triage,
        "actual_score": actual_score,
        "triage_match": triage_match,
        "expected_flags": expected_flags,
        "red_flag_detected": red_flag_detected,
        "response": full_response[:300],
        "tool_count": len([e for e in events if e.type == "tool_start"]),
        "thinking": any(e.type == "thinking" for e in events),
    }

    if verbose:
        icon = "✅" if result["status"] == "pass" else "⚠️"
        print(
            f"  {icon} {case['id']} | {language} | expected={expected_triage} actual={actual_triage} | flags={'🚨' if red_flag_detected else '—'} | tools={result['tool_count']}"
        )
        if not triage_match:
            print(f"     └─ MISMATCH: expected {expected_triage}, got {actual_triage}")
        if expected_flags and not red_flag_detected:
            print(f"     └─ MISSED FLAGS: {expected_flags}")

    return result


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run clinical evaluation cases")
    parser.add_argument("--case", type=str, help="Run a specific case by ID")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--language", type=str, help="Filter by language (ar/en)")
    parser.add_argument(
        "--model", type=str, help="LLM model to use (e.g. groq/qwen/qwen3-32b, oa/gpt-4o)"
    )
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    cases = load_cases()

    # Filter
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]
    if args.language:
        cases = [c for c in cases if c.get("language") == args.language]

    if not cases:
        print("No cases found matching criteria.")
        return

    print(f"\n{'=' * 70}")
    print(f"  MedAgent Clinical Evaluation — {len(cases)} test cases")
    print(f"{'=' * 70}\n")

    model = (
        args.model
        or os.environ.get("EVAL_MODEL")
        or os.environ.get("LLM_MODEL", "qwen/qwen-2.5-72b-instruct")
    )

    # Auto-detect provider from model prefix for logging
    if not args.quiet:
        print(f"  Model: {model}\n")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}]", end=" ")
        result = await run_case(case, model=model, verbose=not args.quiet)
        results.append(result)
        # Small delay between cases to avoid rate limiting
        await asyncio.sleep(1)

    # Summary
    passed = sum(1 for r in results if r["status"] == "pass")
    total = len(results)

    print(f"\n{'=' * 70}")
    print(
        f"  Results: {passed}/{total} passed ({passed / total * 100:.1f}%)"
        if total
        else "  No results"
    )
    print(f"{'=' * 70}")

    # By category
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "pass": 0}
        categories[cat]["total"] += 1
        if r["status"] == "pass":
            categories[cat]["pass"] += 1

    print("\n  By category:")
    for cat, stats in sorted(categories.items()):
        pct = stats["pass"] / stats["total"] * 100 if stats["total"] else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {cat:<16} [{bar}] {stats['pass']}/{stats['total']}")

    # Triage accuracy
    triage_correct = sum(1 for r in results if r["triage_match"] is True)
    triage_total = sum(1 for r in results if r["triage_match"] is not None)
    if triage_total:
        print(
            f"\n  Triage accuracy: {triage_correct}/{triage_total} ({triage_correct / triage_total * 100:.1f}%)"
        )

    # Flag recall
    flag_cases = [r for r in results if r["expected_flags"]]
    flag_detected = sum(1 for r in flag_cases if r["red_flag_detected"])
    if flag_cases:
        print(
            f"  Red-flag recall: {flag_detected}/{len(flag_cases)} ({flag_detected / len(flag_cases) * 100:.1f}%)"
        )

    print()

    # Save results
    output_file = Path(__file__).resolve().parent / "clinical_eval_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Detailed results saved to: {output_file}\n")


if __name__ == "__main__":
    asyncio.run(main())
