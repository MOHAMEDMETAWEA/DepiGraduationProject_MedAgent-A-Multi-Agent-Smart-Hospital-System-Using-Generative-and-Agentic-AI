"""Multi-turn conversation test — 2 models, 3 conversations each"""

import asyncio
import json
import time

import httpx

API = "http://localhost:8000/api/v1"

# 3 conversation scenarios
CONVERSATIONS = [
    {
        "name": "صداع نصفي",
        "turns": [
            "عندي صداع شديد من ٣ أيام",
            "الصداع في نص راسي الشمال ومعاه غثيان",
            "بخف شوية لما اقعد في ضلمة",
        ],
    },
    {
        "name": "ألم في البطن",
        "turns": [
            "عندي الم في بطني من امبارح",
            "الم في الجنب اليمين واسهال",
            "لا مفيش حرارة",
        ],
    },
    {
        "name": "كحة وسخونية",
        "turns": [
            "I have a cough and fever for 5 days",
            "the fever is around 38.5 and I feel very tired",
            "I took paracetamol but it didn't help much",
        ],
    },
]

MODELS = [
    ("groq/meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout"),
    ("groq/qwen/qwen3-32b", "Qwen 3 32B"),
]


async def run_conversation(client, token, model_id, model_name, conv_data):
    results = []
    conv_id = None

    for turn_idx, message in enumerate(conv_data["turns"]):
        try:
            # Create conversation on first turn
            if conv_id is None:
                r = await client.post(
                    f"{API}/conversations",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"title": f"{model_name} - {conv_data['name']}", "language": "ar"},
                )
                conv_id = r.json()["id"]

            # Send message
            start = time.monotonic()
            tokens = 0
            triage = ""
            error = ""
            text = ""

            async with client.stream(
                "POST",
                f"{API}/conversations/{conv_id}/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": message, "model": model_id},
                timeout=45,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        evt = json.loads(line[6:])
                        if evt["type"] == "token":
                            tokens += 1
                            text += evt.get("content", "")
                        elif evt["type"] == "triage":
                            triage = evt.get("data", {}).get("level", "")
                        elif evt["type"] == "error":
                            error = evt.get("content", "")[:80]
                        elif evt["type"] == "done":
                            pass

            latency = (time.monotonic() - start) * 1000
            status = "OK" if tokens > 0 and not error else (error or "EMPTY")
            results.append(
                {
                    "turn": turn_idx + 1,
                    "message": message[:40],
                    "tokens": tokens,
                    "triage": triage,
                    "latency_ms": latency,
                    "status": status,
                    "preview": text[:100].replace("\n", " "),
                }
            )
            print(
                f"  Turn {turn_idx + 1}: {tokens:3d} tok | {latency:5.0f}ms | {triage or '-':8s} | {status}"
            )

        except Exception as e:
            results.append(
                {
                    "turn": turn_idx + 1,
                    "tokens": 0,
                    "latency_ms": 0,
                    "status": str(e)[:60],
                    "preview": "",
                }
            )
            print(f"  Turn {turn_idx + 1}: ERROR: {e}")

        await asyncio.sleep(0.5)

    return results, conv_id


async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        r = await client.post(
            f"{API}/auth/login", json={"email": "test@test.com", "password": "Test1234!"}
        )
        token = r.json()["access_token"]

        print("=" * 70)
        print("Multi-turn Conversation Tests")
        print("=" * 70)

        total_ok = 0
        total_turns = 0

        for model_id, model_name in MODELS:
            print(f"\n{'=' * 70}")
            print(f"  {model_name}")
            print(f"{'=' * 70}")

            for conv in CONVERSATIONS:
                print(f"\n  ── {conv['name']} ──")
                results, _ = await run_conversation(client, token, model_id, model_name, conv)

                ok = sum(1 for r in results if r["tokens"] > 0)
                total_ok += ok
                total_turns += len(results)

                # Show preview of last response
                last = results[-1]
                print(f"  → {ok}/{len(results)} turns OK | Last: {last['preview'][:80]}")

        print(f"\n{'=' * 70}")
        print(
            f"  TOTAL: {total_ok}/{total_turns} turns successful ({total_ok * 100 // max(1, total_turns)}%)"
        )
        print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
