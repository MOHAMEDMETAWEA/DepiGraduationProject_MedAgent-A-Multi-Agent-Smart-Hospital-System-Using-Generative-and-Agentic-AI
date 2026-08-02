"""
T3.03 — Base Model Benchmark

Compares candidate models on 50 triage prompts (AR + EN).
Measures: accuracy, avg latency, token count, refusal rate.

Candidates:
- Qwen2.5-7B (primary — strong Arabic)
- Llama-3.1-8B (backup A — needs translation)
- Jais-13B (backup B — Arabic-first, heavier)

Uses Ollama for inference (local).
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"

# ── Prompt templates per language ──

SYSTEM_PROMPTS = {
    "en": "You are a medical triage assistant. Given a patient's chief complaint, assign a triage level (emergency, urgent, routine) and explain briefly. Respond in JSON.",
    "ar": "أنت مساعد فرز طبي. بناءً على شكوى المريض، حدد مستوى الفرز (طارئ، عاجل، روتيني) واشرح باختصار. أجب بصيغة JSON.",
}

# 50 prompts — 25 EN, 25 AR, covering all triage levels
BENCHMARK_PROMPTS = [
    # ── Emergency (EN) ──
    {
        "id": "E01",
        "lang": "en",
        "complaint": "Chest pain radiating to left arm and jaw, started 10 minutes ago",
        "expected": "emergency",
    },
    {
        "id": "E02",
        "lang": "en",
        "complaint": "Cannot breathe, lips turning blue",
        "expected": "emergency",
    },
    {
        "id": "E03",
        "lang": "en",
        "complaint": "Sudden severe headache with confusion and slurred speech",
        "expected": "emergency",
    },
    {
        "id": "E04",
        "lang": "en",
        "complaint": "Heavy bleeding from wound, won't stop after 10 minutes",
        "expected": "emergency",
    },
    {
        "id": "E05",
        "lang": "en",
        "complaint": "Unconscious, not responding to stimuli",
        "expected": "emergency",
    },
    {
        "id": "E06",
        "lang": "en",
        "complaint": "Severe allergic reaction, throat swelling, can barely swallow",
        "expected": "emergency",
    },
    {
        "id": "E07",
        "lang": "en",
        "complaint": "Seizure lasting more than 3 minutes",
        "expected": "emergency",
    },
    {
        "id": "E08",
        "lang": "en",
        "complaint": "Choking on food, cannot cough or speak",
        "expected": "emergency",
    },
    # ── Emergency (AR) ──
    {
        "id": "E09",
        "lang": "ar",
        "complaint": "ألم في الصدر يمتد للذراع الأيسر والفك، بدأ من ١٠ دقائق",
        "expected": "emergency",
    },
    {
        "id": "E10",
        "lang": "ar",
        "complaint": "لا أستطيع التنفس، شفتاي تزرقان",
        "expected": "emergency",
    },
    {
        "id": "E11",
        "lang": "ar",
        "complaint": "صداع شديد مفاجئ مع تشوش وثقل في الكلام",
        "expected": "emergency",
    },
    {
        "id": "E12",
        "lang": "ar",
        "complaint": "نزيف حاد من جرح، لم يتوقف بعد ١٠ دقائق",
        "expected": "emergency",
    },
    # ── Urgent (EN) ──
    {
        "id": "U01",
        "lang": "en",
        "complaint": "High fever 39.5°C for 3 days, not responding to paracetamol",
        "expected": "urgent",
    },
    {
        "id": "U02",
        "lang": "en",
        "complaint": "Severe abdominal pain on right side, nausea, vomiting",
        "expected": "urgent",
    },
    {
        "id": "U03",
        "lang": "en",
        "complaint": "Difficulty breathing, wheezing, history of asthma",
        "expected": "urgent",
    },
    {
        "id": "U04",
        "lang": "en",
        "complaint": "Blood in urine, burning sensation when urinating",
        "expected": "urgent",
    },
    {
        "id": "U05",
        "lang": "en",
        "complaint": "Fell and hit head, dizzy, slight confusion",
        "expected": "urgent",
    },
    {
        "id": "U06",
        "lang": "en",
        "complaint": "Possible fracture in arm, swelling and severe pain",
        "expected": "urgent",
    },
    {
        "id": "U07",
        "lang": "en",
        "complaint": "Persistent vomiting for 24 hours, cannot keep water down",
        "expected": "urgent",
    },
    {
        "id": "U08",
        "lang": "en",
        "complaint": "Infant 3 months old with fever 38.5°C, irritable",
        "expected": "urgent",
    },
    {
        "id": "U09",
        "lang": "en",
        "complaint": "Eye injury, chemical splash, burning pain",
        "expected": "urgent",
    },
    {
        "id": "U10",
        "lang": "en",
        "complaint": "Deep cut on hand, may need stitches",
        "expected": "urgent",
    },
    # ── Urgent (AR) ──
    {
        "id": "U11",
        "lang": "ar",
        "complaint": "حمى مرتفعة ٣٩.٥ لمدة ٣ أيام، لا تستجيب للباراسيتامول",
        "expected": "urgent",
    },
    {
        "id": "U12",
        "lang": "ar",
        "complaint": "ألم شديد في البطن من الجهة اليمنى، غثيان وقيء",
        "expected": "urgent",
    },
    {
        "id": "U13",
        "lang": "ar",
        "complaint": "صعوبة في التنفس، صفير، تاريخ مرضي بالربو",
        "expected": "urgent",
    },
    {
        "id": "U14",
        "lang": "ar",
        "complaint": "دم في البول، حرقة عند التبول",
        "expected": "urgent",
    },
    {
        "id": "U15",
        "lang": "ar",
        "complaint": "سقطت وضربت رأسي، دوخة، تشوش بسيط",
        "expected": "urgent",
    },
    {
        "id": "U16",
        "lang": "ar",
        "complaint": "كسر محتمل في الذراع، تورم وألم شديد",
        "expected": "urgent",
    },
    {
        "id": "U17",
        "lang": "ar",
        "complaint": "قيء مستمر لمدة ٢٤ ساعة، لا أستطيع الاحتفاظ بالماء",
        "expected": "urgent",
    },
    {
        "id": "U18",
        "lang": "ar",
        "complaint": "رضيع عمره ٣ أشهر مع حمى ٣٨.٥، سريع الانفعال",
        "expected": "urgent",
    },
    # ── Routine (EN) ──
    {
        "id": "R01",
        "lang": "en",
        "complaint": "Mild headache for 2 days, relieved by rest",
        "expected": "routine",
    },
    {
        "id": "R02",
        "lang": "en",
        "complaint": "Runny nose, sneezing, seasonal allergies",
        "expected": "routine",
    },
    {
        "id": "R03",
        "lang": "en",
        "complaint": "Minor rash on arm, not spreading, no fever",
        "expected": "routine",
    },
    {
        "id": "R04",
        "lang": "en",
        "complaint": "Feeling tired lately, trouble sleeping",
        "expected": "routine",
    },
    {
        "id": "R05",
        "lang": "en",
        "complaint": "Sore throat for 1 day, no fever",
        "expected": "routine",
    },
    {
        "id": "R06",
        "lang": "en",
        "complaint": "Occasional heartburn after eating spicy food",
        "expected": "routine",
    },
    {
        "id": "R07",
        "lang": "en",
        "complaint": "Constipation for 3 days, no pain",
        "expected": "routine",
    },
    {
        "id": "R08",
        "lang": "en",
        "complaint": "Mild back pain after lifting heavy objects",
        "expected": "routine",
    },
    {
        "id": "R09",
        "lang": "en",
        "complaint": "Dry cough for 5 days, no other symptoms",
        "expected": "routine",
    },
    {
        "id": "R10",
        "lang": "en",
        "complaint": "Small bruise on leg, no swelling",
        "expected": "routine",
    },
    {
        "id": "R11",
        "lang": "en",
        "complaint": "Mild joint pain in knees, worse in morning",
        "expected": "routine",
    },
    {
        "id": "R12",
        "lang": "en",
        "complaint": "Skin dryness and itching, no rash",
        "expected": "routine",
    },
    # ── Routine (AR) ──
    {
        "id": "R13",
        "lang": "ar",
        "complaint": "صداع خفيف منذ يومين، يتحسن بالراحة",
        "expected": "routine",
    },
    {
        "id": "R14",
        "lang": "ar",
        "complaint": "رشح وعطس، حساسية موسمية",
        "expected": "routine",
    },
    {
        "id": "R15",
        "lang": "ar",
        "complaint": "طفح جلدي بسيط على الذراع، لا ينتشر، لا حمى",
        "expected": "routine",
    },
    {
        "id": "R16",
        "lang": "ar",
        "complaint": "شعور بالتعب مؤخراً، صعوبة في النوم",
        "expected": "routine",
    },
    {
        "id": "R17",
        "lang": "ar",
        "complaint": "التهاب حلق منذ يوم، لا حمى",
        "expected": "routine",
    },
    {
        "id": "R18",
        "lang": "ar",
        "complaint": "حرقة معدة بعد الأكل الحار",
        "expected": "routine",
    },
    {
        "id": "R19",
        "lang": "ar",
        "complaint": "إمساك منذ ٣ أيام، لا ألم",
        "expected": "routine",
    },
    {
        "id": "R20",
        "lang": "ar",
        "complaint": "ألم خفيف في الظهر بعد حمل أشياء ثقيلة",
        "expected": "routine",
    },
]


@dataclass
class BenchmarkResult:
    model: str
    total: int = 0
    correct: int = 0
    errors: int = 0
    total_latency_ms: float = 0
    responses: list[dict] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total > 0 else 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total if self.total > 0 else 0


async def run_benchmark(models: list[str], output_dir: Path) -> dict[str, BenchmarkResult]:
    """
    Run benchmark across models on the 50 prompts.

    Each model is tested on all 50 prompts.
    Results saved to output_dir/model_name.jsonl
    """
    results: dict[str, BenchmarkResult] = {}

    for model in models:
        print(f"\n{'=' * 60}")
        print(f"Benchmarking: {model}")
        print(f"{'=' * 60}")

        result = BenchmarkResult(model=model)
        output_file = output_dir / f"benchmark_{model.replace(':', '_')}.jsonl"

        async with httpx.AsyncClient(timeout=60) as client:
            for prompt in BENCHMARK_PROMPTS:
                lang = prompt["lang"]
                system = SYSTEM_PROMPTS[lang]
                user = f"Chief complaint: {prompt['complaint']}\n\nRespond with JSON: {{'triage': 'emergency|urgent|routine', 'reasoning': '...'}}"

                start = time.time()
                try:
                    resp = await client.post(
                        OLLAMA_URL,
                        json={
                            "model": model,
                            "system": system,
                            "prompt": user,
                            "stream": False,
                            "options": {"temperature": 0.1},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data.get("response", "")
                    latency = (time.time() - start) * 1000

                    # Parse triage from response
                    predicted = parse_triage(response_text)
                    expected = prompt["expected"]
                    correct = predicted == expected

                    result.total += 1
                    if correct:
                        result.correct += 1
                    result.total_latency_ms += latency

                    entry = {
                        "id": prompt["id"],
                        "lang": lang,
                        "complaint": prompt["complaint"],
                        "expected": expected,
                        "predicted": predicted,
                        "correct": correct,
                        "latency_ms": round(latency, 1),
                        "response": response_text[:200],
                    }
                    result.responses.append(entry)

                    icon = "✅" if correct else "❌"
                    print(
                        f"  {icon} {prompt['id']} ({prompt['lang']}): {predicted} (expected {expected}) — {latency:.0f}ms"
                    )

                except Exception as e:
                    result.total += 1
                    result.errors += 1
                    print(f"  ❌ {prompt['id']}: ERROR — {e}")

        # Save detailed results
        with open(output_file, "w", encoding="utf-8") as f:
            for r in result.responses:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        results[model] = result
        print(
            f"\n  Accuracy: {result.accuracy:.1%} | Avg latency: {result.avg_latency_ms:.0f}ms | Errors: {result.errors}"
        )

    return results


def parse_triage(text: str) -> str:
    """Extract triage level from model response."""

    text_lower = text.lower()
    if "emergency" in text_lower or "طارئ" in text:
        return "emergency"
    if "urgent" in text_lower or "عاجل" in text:
        return "urgent"
    if "routine" in text_lower or "روتيني" in text:
        return "routine"
    return "unknown"


def print_comparison(results: dict[str, BenchmarkResult]):
    """Print comparison table."""
    print("\n")
    print("=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)
    print(f"{'Model':<25} {'Accuracy':>10} {'Avg Latency':>12} {'Errors':>8}")
    print("-" * 70)

    for model_name, r in results.items():
        print(f"{model_name:<25} {r.accuracy:>9.1%} {r.avg_latency_ms:>10.0f}ms {r.errors:>8}")

    # Pick winner
    if results:
        winner = max(results.values(), key=lambda r: r.accuracy)
        print("\n" + "=" * 70)
        print(f"WINNER: {winner.model} — Accuracy: {winner.accuracy:.1%}")
        print("=" * 70)


if __name__ == "__main__":
    import asyncio

    MODELS = [
        "qwen3.5:cloud",
        "qwen3.6",  # Llama alternative — qwen for Arabic
    ]

    output_dir = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("MedAgent — T3.03 Base Model Benchmark")
    print(
        f"Prompts: {len(BENCHMARK_PROMPTS)} ({sum(1 for p in BENCHMARK_PROMPTS if p['lang'] == 'en')} EN + {sum(1 for p in BENCHMARK_PROMPTS if p['lang'] == 'ar')} AR)"
    )
    print(f"Models: {MODELS}")

    results = asyncio.run(run_benchmark(MODELS, output_dir))
    print_comparison(results)
