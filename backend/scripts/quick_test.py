"""Quick test — 10 prompts per model"""

import asyncio
import json
import time

import httpx

API = "http://localhost:8000/api/v1"
PROMPTS = [
    "السلام عليكم",
    "عندي صداع خفيف من يومين",
    "عندي الم شديد في بطني مع اسهال",
    "I have a mild cough for 3 days",
    "I have severe chest pain radiating to my left arm",
    "عندي حساسية موسمية وعطس كتير",
    "what should I do for a sprained ankle",
    "عندي اكتئاب ومش قادر اقوم من السرير",
    "I have a fever of 39 for 4 days",
    "عندي دوخه وفقدان توازن",
]

MODELS = [
    ("groq/qwen/qwen3-32b", "Qwen 3 32B"),
    ("groq/llama-3.3-70b-versatile", "Llama 3.3 70B"),
    ("groq/allam-2-7b", "Allam 2 7B"),
    ("groq/meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout"),
    ("groq/llama-3.1-8b-instant", "Llama 3.1 8B"),
]


async def test_model(client, token, model_id, model_name):
    results = []
    for i, prompt in enumerate(PROMPTS):
        try:
            # Create conversation
            r = await client.post(
                f"{API}/conversations",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": f"test-{i}", "language": "ar"},
            )
            conv_id = r.json()["id"]

            # Stream chat
            start = time.monotonic()
            tokens = 0
            triage = ""
            error = ""
            done = False

            async with client.stream(
                "POST",
                f"{API}/conversations/{conv_id}/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": prompt, "model": model_id},
                timeout=30,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        evt = json.loads(line[6:])
                        if evt["type"] == "token":
                            tokens += 1
                        elif evt["type"] == "triage":
                            triage = evt.get("data", {}).get("level", "")
                        elif evt["type"] == "error":
                            error = evt.get("content", "")[:80]
                        elif evt["type"] == "done":
                            done = True

            latency = (time.monotonic() - start) * 1000
            status = "OK" if done and not error else (error or "TIMEOUT")
            results.append((i + 1, tokens, triage, latency, status))
            print(
                f"  [{i + 1:2d}/10] {tokens:3d} tok | {latency:5.0f}ms | {triage or '-':8s} | {status}"
            )

        except Exception as e:
            results.append((i + 1, 0, "", 0, str(e)[:60]))
            print(f"  [{i + 1:2d}/10] ERROR: {e}")

        await asyncio.sleep(0.5)

    return results


async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        # Login
        r = await client.post(
            f"{API}/auth/login", json={"email": "test@test.com", "password": "Test1234!"}
        )
        token = r.json()["access_token"]

        print("=" * 70)
        print("MedAgent Model Testing — 10 prompts per model")
        print("=" * 70)
        print()

        all_results = {}

        for model_id, model_name in MODELS:
            print(f"\n── {model_name} ({model_id}) ──")
            results = await test_model(client, token, model_id, model_name)
            all_results[model_name] = results

            ok = sum(1 for _, t, _, _, s in results if t > 0 and s == "OK")
            avg_lat = sum(lat for _, _, _, lat, _ in results if lat > 0) / max(
                1, sum(1 for _, _, _, lat, _ in results if lat > 0)
            )
            avg_tok = sum(t for _, t, _, _, _ in results) / len(results)
            print(f"  → {ok}/10 passed | avg {avg_lat:.0f}ms | avg {avg_tok:.0f} tok")

        # Final report
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"{'Model':<20} {'Pass':>5} {'Avg ms':>7} {'Avg tok':>8} {'Issues'}")
        print("-" * 55)

        for model_name, results in all_results.items():
            ok = sum(1 for _, t, _, _, s in results if t > 0 and s == "OK")
            avg_lat = sum(lat for _, _, _, lat, _ in results if lat > 0) / max(
                1, sum(1 for _, _, _, lat, _ in results if lat > 0)
            )
            avg_tok = sum(t for _, t, _, _, _ in results) / len(results)
            issues = [f"#{i}" for i, t, _, _, s in results if t == 0 or s != "OK"]
            issue_str = ", ".join(issues) if issues else "none"
            print(f"{model_name:<20} {ok:>4}/10 {avg_lat:>6.0f} {avg_tok:>7.0f}  {issue_str}")


if __name__ == "__main__":
    asyncio.run(main())
