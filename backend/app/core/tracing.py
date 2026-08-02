"""OpenTelemetry tracing — agent loop spans + FastAPI auto-instrumentation.

Spans never carry PHI text — only IDs, model names, and durations.
"""

from __future__ import annotations

import os
from contextlib import contextmanager, suppress

_TRACER = None


def _maybe_init() -> None:
    """Lazily initialise OTel — no-ops if SDK not installed or disabled."""
    global _TRACER
    if _TRACER is not None:
        return

    if os.environ.get("OTEL_DISABLED", "").lower() in ("1", "true", "yes"):
        _TRACER = _NoopTracer()
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        provider = TracerProvider(resource=Resource.create({"service.name": "medagent-backend"}))
        # Use ConsoleSpanExporter as a default safe sink — swap for OTLP in prod.
        exporter_kind = os.environ.get("OTEL_EXPORTER", "console").lower()
        if exporter_kind == "otlp":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            except ImportError:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("medagent")
    except ImportError:
        _TRACER = _NoopTracer()


def instrument_fastapi(app) -> None:
    """Auto-instrument a FastAPI app — silently no-ops if otel-fastapi missing."""
    _maybe_init()
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass


class _NoopSpan:
    def set_attribute(self, *_a, **_kw) -> None:
        pass

    def add_event(self, *_a, **_kw) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class _NoopTracer:
    def start_as_current_span(self, *_a, **_kw):
        return _NoopSpan()


@contextmanager
def span(name: str, **attributes):
    """Context manager that opens an OTel span. Sets attributes on the span body.

    Never includes PHI text — only IDs, model names, and counts.
    """
    _maybe_init()
    if _TRACER is None or isinstance(_TRACER, _NoopTracer):
        yield _NoopSpan()
        return

    with _TRACER.start_as_current_span(name) as s:
        for k, v in attributes.items():
            with suppress(Exception):
                s.set_attribute(k, v)
        yield s
