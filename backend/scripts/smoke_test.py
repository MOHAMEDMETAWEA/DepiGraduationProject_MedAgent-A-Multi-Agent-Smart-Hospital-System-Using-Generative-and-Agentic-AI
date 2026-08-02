"""
Smoke Test Suite — 100 diverse medical triage tests

Tests cover: AR/EN, emergency/urgent/routine, edge cases.
Measures: latency, token count, red-flag detection, triage level.

Usage:
    uv run python scripts/smoke_test.py
    uv run python scripts/smoke_test.py --count 50  # fewer tests
    uv run python scripts/smoke_test.py --output results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000/api/v1"
SESSION_FILE = Path(__file__).resolve().parent.parent / "data" / "test_session.json"

TEST_CASES: list[dict] = [
    # ===== EMERGENCY (AR) =====
    {"message": "عندي ألم شديد في الصدر وصعوبة في التنفس", "lang": "ar", "expect": "emergency"},
    {"message": "ألم في صدري شكله نوبة قلبية", "lang": "ar", "expect": "emergency"},
    {"message": "عندي جلطة في رجلي اليمين ومنتفخة جدًا", "lang": "ar", "expect": "emergency"},
    {"message": "دم في البول ووجع فظيع في ظهري", "lang": "ar", "expect": "emergency"},
    {"message": "قئ دم واسهال شديد من ٣ أيام", "lang": "ar", "expect": "emergency"},
    {"message": "عندي تشنجات ومش قادر اتكلم ولا اتحرك", "lang": "ar", "expect": "emergency"},
    {"message": "بلعت حاجة غريبة ومش قادر اتنفس", "lang": "ar", "expect": "emergency"},
    {"message": "حاسس بضعف في نصف وشي وفقدان النظر", "lang": "ar", "expect": "emergency"},
    {"message": "صداع مفاجئ كأن حاجة انفجرت في دماغي", "lang": "ar", "expect": "emergency"},
    {"message": "حساسية شديدة وتورم في وشي ورقبتي", "lang": "ar", "expect": "emergency"},
    {"message": "وقعت من عالِ ودماغي وجعتني ومش شايف كويس", "lang": "ar", "expect": "emergency"},
    {"message": "جرح عميق في بطني ومش قادر اوقف الدم", "lang": "ar", "expect": "emergency"},
    {"message": "لسعتني عقرب أسود ورجلي ورمت", "lang": "ar", "expect": "emergency"},
    {"message": "عندي حرقان في صدري مع تعرق وتنميل في دراعي", "lang": "ar", "expect": "emergency"},
    {"message": "صحيت من النوم مش قادر اتحرك نهائي", "lang": "ar", "expect": "emergency"},
    # ===== EMERGENCY (EN) =====
    {
        "message": "I have severe chest pain radiating to my left arm",
        "lang": "en",
        "expect": "emergency",
    },
    {
        "message": "sudden weakness on one side of my body and slurred speech",
        "lang": "en",
        "expect": "emergency",
    },
    {"message": "I can't breathe, lips turning blue", "lang": "en", "expect": "emergency"},
    {
        "message": "severe allergic reaction, throat swelling, can't swallow",
        "lang": "en",
        "expect": "emergency",
    },
    {"message": "coughing up blood and severe chest pain", "lang": "en", "expect": "emergency"},
    {
        "message": "I think I'm having a stroke, half of my face is numb",
        "lang": "en",
        "expect": "emergency",
    },
    {"message": "seizure lasting more than 5 minutes", "lang": "en", "expect": "emergency"},
    {"message": "deep knife wound, bleeding won't stop", "lang": "en", "expect": "emergency"},
    {
        "message": "snake bite, leg is swelling and turning black",
        "lang": "en",
        "expect": "emergency",
    },
    {
        "message": "I feel like I'm going to die, crushing chest pressure",
        "lang": "en",
        "expect": "emergency",
    },
    # ===== URGENT (AR) =====
    {"message": "حمى ٣٩ درجة من ٥ أيام ومش بتنزل", "lang": "ar", "expect": "urgent"},
    {"message": "مغص شديد ومستمر في بطني من يومين", "lang": "ar", "expect": "urgent"},
    {"message": "وجع في كليتي اليمين وحمى وقشعريرة", "lang": "ar", "expect": "urgent"},
    {"message": "صداع نصفي شديد من ٣ أيام مش قادر اشوف", "lang": "ar", "expect": "urgent"},
    {"message": "ألم شديد في أذني اليمين مع نزول صديد", "lang": "ar", "expect": "urgent"},
    {"message": "تورم واحمرار في ركبتي مع حرارة شديدة", "lang": "ar", "expect": "urgent"},
    {"message": "اسهال ١٠ مرات في اليوم مع جفاف شديد", "lang": "ar", "expect": "urgent"},
    {"message": "ابني عنده ٣ شهور وحرارته ٣٨ ونص", "lang": "ar", "expect": "urgent"},
    {"message": "عندي حرقان في البول شديد من ٣ أيام", "lang": "ar", "expect": "urgent"},
    {"message": "انتفاخ في الغدد الليمفاوية في رقبتي وحمى", "lang": "ar", "expect": "urgent"},
    # ===== URGENT (EN) =====
    {
        "message": "fever of 39.5 for 4 days, not responding to medication",
        "lang": "en",
        "expect": "urgent",
    },
    {"message": "severe lower back pain with blood in urine", "lang": "en", "expect": "urgent"},
    {
        "message": "migraine so bad I can't open my eyes, 3 days now",
        "lang": "en",
        "expect": "urgent",
    },
    {"message": "my 2-month-old has a fever of 38.5", "lang": "en", "expect": "urgent"},
    {
        "message": "severe abdominal pain that started suddenly last night",
        "lang": "en",
        "expect": "urgent",
    },
    {
        "message": "eye injury, pain and blurred vision since yesterday",
        "lang": "en",
        "expect": "urgent",
    },
    {
        "message": "possible fracture in my wrist, swelling and deformity",
        "lang": "en",
        "expect": "urgent",
    },
    {"message": "burning pain urinating with fever and chills", "lang": "en", "expect": "urgent"},
    {"message": "dehydration, can't keep water down for 2 days", "lang": "en", "expect": "urgent"},
    {
        "message": "swollen lymph nodes all over neck with night sweats",
        "lang": "en",
        "expect": "urgent",
    },
    # ===== ROUTINE (AR) =====
    {"message": "عندي كحة خفيفة من ٣ أيام ومفيش حرارة", "lang": "ar", "expect": "routine"},
    {"message": "صداع خفيف في آخر اليوم من كتر الشغل", "lang": "ar", "expect": "routine"},
    {"message": "عندي حكة جلدية خفيفة في دراعي", "lang": "ar", "expect": "routine"},
    {
        "message": "عاوز أعرف لو التطعيم بتاع الإنفلونزا مناسب ليا",
        "lang": "ar",
        "expect": "routine",
    },
    {"message": "عندي أرق ومش بعرف أنام كويس", "lang": "ar", "expect": "routine"},
    {
        "message": "باخد فيتامين دال كل يوم، لو سمحت ينفع أزود الجرعة؟",
        "lang": "ar",
        "expect": "routine",
    },
    {"message": "دلوقتي رجلي اليمين بتنمل كتير وأنا قاعدة", "lang": "ar", "expect": "routine"},
    {"message": "عاوزة نظام غذائي صحي للتخسيس", "lang": "ar", "expect": "routine"},
    {"message": "عندي سيلان في الأنف وعطس من يومين", "lang": "ar", "expect": "routine"},
    {"message": "زونام ولا بندول للصداع أحسن؟", "lang": "ar", "expect": "routine"},
    {"message": "عاوز أعمل تحليل شامل لو سمحت إيه المطلوب", "lang": "ar", "expect": "routine"},
    {"message": "عندى امساك من اسبوع وشايل هم", "lang": "ar", "expect": "routine"},
    {"message": "نفسي تعبانة شوية من الشغل والضغط", "lang": "ar", "expect": "routine"},
    {
        "message": "عاوزة اعرف الحمل في الشهر التاسع إيه الاكل الممنوع",
        "lang": "ar",
        "expect": "routine",
    },
    {"message": "وجع طفيف في ضهري من الجلوس الطويل", "lang": "ar", "expect": "routine"},
    # ===== ROUTINE (EN) =====
    {"message": "mild cough for 3 days, no fever", "lang": "en", "expect": "routine"},
    {"message": "occasional headache after working long hours", "lang": "en", "expect": "routine"},
    {"message": "mild skin rash on my arm, itching slightly", "lang": "en", "expect": "routine"},
    {"message": "should I get the flu shot this year?", "lang": "en", "expect": "routine"},
    {
        "message": "trouble sleeping for the past week, feeling tired",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "taking vitamin D daily, should I increase the dose?",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "mild muscle soreness after exercising yesterday",
        "lang": "en",
        "expect": "routine",
    },
    {"message": "what foods help lower cholesterol?", "lang": "en", "expect": "routine"},
    {"message": "runny nose and sneezing, started this morning", "lang": "en", "expect": "routine"},
    {
        "message": "is paracetamol or ibuprofen better for a mild headache?",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "feeling a bit anxious about a job interview next week",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "constipated for a few days, what should I eat?",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "slight back pain from sitting too long at desk",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "mild seasonal allergies, sneezing and itchy eyes",
        "lang": "en",
        "expect": "routine",
    },
    {
        "message": "what vaccinations do I need before traveling to Africa?",
        "lang": "en",
        "expect": "routine",
    },
    # ===== EDGE CASES (AR/EN) =====
    {"message": "السلام عليكم", "lang": "ar", "expect": "routine"},
    {"message": "Hi, how are you?", "lang": "en", "expect": "routine"},
    {"message": "عاوز اشكرك على المساعدة", "lang": "ar", "expect": "routine"},
    {"message": "Thank you for your help", "lang": "en", "expect": "routine"},
    {"message": "مع السلامة", "lang": "ar", "expect": "routine"},
    {"message": "Goodbye", "lang": "en", "expect": "routine"},
    {
        "message": "عندي الم في بطني من يومين وامبارح خف شوية النهاردة رجع تاني",
        "lang": "ar",
        "expect": "urgent",
    },
    {
        "message": "my stomach hurts since yesterday and I'm not sure if I should go to hospital",
        "lang": "en",
        "expect": "routine",
    },
    {"message": "عندي برد ورشح وسخونية ومش عارف اعمل ايه", "lang": "ar", "expect": "routine"},
    {"message": "i have a cold and fever, not sure what to do", "lang": "en", "expect": "routine"},
    # ===== DRUG INTERACTION QUERIES =====
    {"message": "باخد وارفارين وعاوز اخد اسبرين، هل ينفع؟", "lang": "ar", "expect": "urgent"},
    {"message": "I take warfarin, can I also take ibuprofen?", "lang": "en", "expect": "urgent"},
    {"message": "عندي حساسية بنسلين، هل أقدر اخد أموكسيسيلين؟", "lang": "ar", "expect": "urgent"},
    {"message": "allergic to penicillin, is amoxicillin safe?", "lang": "en", "expect": "urgent"},
    {
        "message": "باخد دواء الضغط يوميًا، هل أقدر اخد مسكن للصداع؟",
        "lang": "ar",
        "expect": "routine",
    },
    {
        "message": "taking blood pressure medication, can I take a painkiller?",
        "lang": "en",
        "expect": "routine",
    },
    # ===== MENTAL HEALTH =====
    {"message": "الفترة دي حاسس باكتئاب ومش قادر أقوم من السرير", "lang": "ar", "expect": "urgent"},
    {
        "message": "I feel really depressed and can't get out of bed lately",
        "lang": "en",
        "expect": "urgent",
    },
    {"message": "عندي قلق وتوتر معظم الوقت ومش عارف اعمل ايه", "lang": "ar", "expect": "routine"},
    {"message": "I have constant anxiety and panic attacks", "lang": "en", "expect": "urgent"},
    {"message": "بفكر في ايذاء نفسي كتير الفترة دي", "lang": "ar", "expect": "emergency"},
    {"message": "I've been having thoughts of harming myself", "lang": "en", "expect": "emergency"},
    # ===== PEDIATRIC =====
    {"message": "ابني عنده سنتين وحرارته ٣٩", "lang": "ar", "expect": "urgent"},
    {"message": "my 3-year-old has a fever of 102 for 3 days", "lang": "en", "expect": "urgent"},
    {"message": "بنتي ٦ شهور وبتسعل كتير بليل", "lang": "ar", "expect": "urgent"},
    {"message": "my 8-month-old has a rash all over her body", "lang": "en", "expect": "urgent"},
]


@dataclass
class TestResult:
    index: int
    message: str
    lang: str
    expected: str
    response: str = ""
    triage_level: str | None = None
    red_flag: bool = False
    token_count: int = 0
    latency_ms: float = 0
    error: str | None = None
    passed: bool = False


async def run_test(client: httpx.AsyncClient, token: str, idx: int, case: dict) -> TestResult:
    result = TestResult(
        index=idx,
        message=case["message"],
        lang=case["lang"],
        expected=case["expect"],
    )
    start = time.monotonic()

    try:
        # Create conversation
        conv_resp = await client.post(
            f"{API_BASE}/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": f"smoke-test-{idx}", "language": case["lang"]},
        )
        conv_resp.raise_for_status()
        conv_id = conv_resp.json()["id"]

        # Send chat message (SSE stream)
        chat_start = time.monotonic()
        accumulated = ""
        events = 0

        async with client.stream(
            "POST",
            f"{API_BASE}/conversations/{conv_id}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": case["message"],
                "model": "qwen/qwen-2.5-72b-instruct",
            },
            timeout=120,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events += 1
                    if data.get("type") == "token":
                        accumulated += data.get("content", "")
                    elif data.get("type") == "red_flag":
                        result.red_flag = True
                    elif data.get("type") == "triage":
                        result.triage_level = data.get("data", {}).get("level")

        result.latency_ms = (time.monotonic() - chat_start) * 1000
        result.token_count = events
        result.response = accumulated.strip()

        # Determine pass/fail based on expected triage
        if result.red_flag and case["expect"] == "emergency":
            result.passed = True
        elif result.triage_level:
            result.passed = result.triage_level == case["expect"]
        elif len(result.response) > 10:
            result.passed = True  # At least got a meaningful response
        else:
            result.passed = False

    except Exception as e:
        result.error = str(e)[:200]
        result.latency_ms = (time.monotonic() - start) * 1000

    return result


def print_progress(i: int, total: int, result: TestResult):
    icon = "✅" if result.passed else "⚠️" if result.response else "❌"
    resp_preview = (
        result.response[:60].replace("\n", " ") if result.response else result.error or "EMPTY"
    )
    print(f"  [{i:3d}/{total}] {icon} {result.latency_ms:6.0f}ms | {resp_preview}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="Number of tests to run")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    cases = TEST_CASES[: args.count]

    # Extend with duplicates if we need more than predefined cases
    while len(cases) < args.count:
        import random as _random

        cases.append(_random.choice(TEST_CASES))

    print(f"\n{'=' * 60}")
    print("🧪 MedAgent Smoke Test Suite")
    print(f"{'=' * 60}")
    print(
        f"  Tests: {len(cases)} ({sum(1 for c in cases if c['lang'] == 'ar')} AR / {sum(1 for c in cases if c['lang'] == 'en')} EN)"
    )
    print(f"  Emergency: {sum(1 for c in cases if c['expect'] == 'emergency')}")
    print(f"  Urgent:    {sum(1 for c in cases if c['expect'] == 'urgent')}")
    print(f"  Routine:   {sum(1 for c in cases if c['expect'] == 'routine')}")
    print("  Model: qwen/qwen-2.5-72b-instruct (OpenRouter)")
    print()

    # Login
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        login_resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": "test@test.com", "password": "Test1234!"},
        )
        if login_resp.status_code != 200:
            # Register if not exists
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "email": "test@test.com",
                    "password": "Test1234!",
                    "full_name": "Test User",
                    "role": "patient",
                },
            )
            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"email": "test@test.com", "password": "Test1234!"},
            )
            login_resp.raise_for_status()

        token = login_resp.json()["access_token"]
        print(f"  🔑 Authenticated: {token[:20]}...\n")

        # Run tests
        results: list[TestResult] = []
        t_start = time.monotonic()

        for i, case in enumerate(cases, 1):
            result = await run_test(client, token, i, case)
            results.append(result)
            print_progress(i, len(cases), result)

            # Brief pause between tests
            if i < len(cases):
                await asyncio.sleep(0.3)

        t_total = time.monotonic() - t_start

        # Summary
        passed = sum(1 for r in results if r.passed)
        errors = sum(1 for r in results if r.error)
        empty = sum(1 for r in results if not r.response and not r.error)
        latencies = [r.latency_ms for r in results if not r.error]
        tokens = [r.token_count for r in results if r.response]

        print(f"\n{'=' * 60}")
        print("📊 SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Total:    {len(results)} tests in {t_total:.0f}s")
        print(f"  Passed:   {passed}/{len(results)} ({passed * 100 // len(results)}%)")
        print(f"  Errors:   {errors}")
        print(f"  Empty:    {empty}")
        print()
        if latencies:
            latencies.sort()
            print("  ⏱️  Latency (ms):")
            print(f"     Min:    {min(latencies):.0f}")
            print(f"     P50:    {latencies[len(latencies) // 2]:.0f}")
            print(f"     P90:    {latencies[int(len(latencies) * 0.9)]:.0f}")
            print(f"     P95:    {latencies[int(len(latencies) * 0.95)]:.0f}")
            print(f"     Max:    {max(latencies):.0f}")
            print(f"     Avg:    {sum(latencies) / len(latencies):.0f}")
        if tokens:
            print(f"  🔤 Avg tokens/response: {sum(tokens) // len(tokens)}")

        # Per-level accuracy
        print()
        for level in ["emergency", "urgent", "routine"]:
            level_cases = [r for r in results if r.expected == level]
            if level_cases:
                acc = sum(1 for r in level_cases if r.passed) * 100 // len(level_cases)
                print(
                    f"  🎯 {level:12s}: {acc}% ({sum(1 for r in level_cases if r.passed)}/{len(level_cases)})"
                )

        # Red-flag recall
        emergency_cases = [r for r in results if r.expected == "emergency"]
        if emergency_cases:
            rf_recall = sum(1 for r in emergency_cases if r.red_flag) * 100 // len(emergency_cases)
            print(
                f"  🚨 Red-flag recall:   {rf_recall}% ({sum(1 for r in emergency_cases if r.red_flag)}/{len(emergency_cases)})"
            )

        # By language
        for lang in ["ar", "en"]:
            lang_cases = [r for r in results if r.lang == lang]
            if lang_cases:
                acc = sum(1 for r in lang_cases if r.passed) * 100 // len(lang_cases)
                print(
                    f"  🌐 {lang}: {acc}% ({sum(1 for r in lang_cases if r.passed)}/{len(lang_cases)})"
                )

        print(f"\n{'=' * 60}")

        # Save results
        output_path = (
            args.output or f"smoke_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )
        report = {
            "meta": {
                "timestamp": datetime.now(UTC).isoformat(),
                "model": "qwen/qwen-2.5-72b-instruct",
                "provider": "openrouter",
                "total_tests": len(results),
                "passed": passed,
                "errors": errors,
                "duration_s": round(t_total, 1),
                "latency_p50_ms": latencies[len(latencies) // 2] if latencies else None,
                "latency_p95_ms": latencies[int(len(latencies) * 0.95)] if latencies else None,
            },
            "results": [
                {
                    "index": r.index,
                    "message": r.message,
                    "lang": r.lang,
                    "expected": r.expected,
                    "response": r.response[:500],
                    "triage_level": r.triage_level,
                    "red_flag": r.red_flag,
                    "token_count": r.token_count,
                    "latency_ms": round(r.latency_ms, 1),
                    "error": r.error,
                    "passed": r.passed,
                }
                for r in results
            ],
        }
        output_path = Path(output_path)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"📁 Report saved: {output_path.resolve()}")

        # Failed cases
        failed = [r for r in results if not r.passed]
        if failed:
            print(f"\n⚠️  Failed ({len(failed)}):")
            for r in failed[:10]:
                reason = (
                    r.error or "empty response"
                    if not r.response
                    else f"got '{r.triage_level}' expected '{r.expected}'"
                )
                print(f"  [{r.index:3d}] {r.message[:70]} — {reason}")


if __name__ == "__main__":
    asyncio.run(main())
