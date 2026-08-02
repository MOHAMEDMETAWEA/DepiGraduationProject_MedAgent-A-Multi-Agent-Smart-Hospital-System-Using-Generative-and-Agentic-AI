"""
T3.07 — MLflow Integration

Tracks model experiments and inference metrics.
- Training runs logged in T3.04
- Inference metrics logged per response (latency, hallucination score)

Usage:
    from app.ai.mlflow_client import log_inference
    await log_inference(model="medagent-lora", latency=1.2, tokens=150, hallucination=0.05)
"""

from __future__ import annotations

import os

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "")
MLFLOW_ENABLED = bool(MLFLOW_TRACKING_URI)


async def log_inference(
    *,
    model_version: str = "base",
    latency_seconds: float = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    hallucination_score: float | None = None,
    triage_level: str | None = None,
    language: str = "en",
    conversation_id: str | None = None,
) -> None:
    """
    Log inference metrics to MLflow.

    Fire-and-forget — never blocks or raises.
    """
    if not MLFLOW_ENABLED:
        return

    try:
        import mlflow

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        metrics = {
            "latency_seconds": latency_seconds,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
        if hallucination_score is not None:
            metrics["hallucination_score"] = hallucination_score

        tags = {
            "model_version": model_version,
            "language": language,
        }
        if triage_level:
            tags["triage_level"] = triage_level
        if conversation_id:
            tags["conversation_id"] = str(conversation_id)

        mlflow.log_metrics(metrics)
        mlflow.set_tags(tags)

    except Exception:
        pass


def get_production_model() -> str | None:
    """
    Fetch the latest production-tagged model from MLflow registry.

    Returns model URI or None if not available.
    """
    if not MLFLOW_ENABLED:
        return None

    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient()

        # Find latest version with "production" stage
        versions = client.get_latest_versions("medagent-lora", stages=["production"])
        if versions:
            return versions[0].source
    except Exception:
        pass

    return None
