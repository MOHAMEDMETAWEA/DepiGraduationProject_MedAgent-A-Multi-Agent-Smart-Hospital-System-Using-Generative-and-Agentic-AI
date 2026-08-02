"""Prometheus metrics — emitted from agent loop, tools, and HTTP layer.

Used by `GET /metrics`. All metric values are best-effort — never let
metric emission fail a real request.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import contextmanager, suppress
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _AVAILABLE = True
except ImportError:  # pragma: no cover — graceful degradation in dev
    _AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest(*_args, **_kwargs) -> bytes:
        return b"# prometheus_client not installed\n"


# ── Registry — isolated so tests don't pollute the default ──
registry: CollectorRegistry | None = CollectorRegistry() if _AVAILABLE else None


def _counter(name: str, doc: str, labels: tuple[str, ...] = ()):
    if not _AVAILABLE:
        return _Noop()
    return Counter(name, doc, labelnames=labels, registry=registry)


def _histogram(name: str, doc: str, labels: tuple[str, ...] = (), buckets=None):
    if not _AVAILABLE:
        return _Noop()
    kwargs: dict = {"labelnames": labels, "registry": registry}
    if buckets is not None:
        kwargs["buckets"] = buckets
    return Histogram(name, doc, **kwargs)


def _gauge(name: str, doc: str, labels: tuple[str, ...] = ()):
    if not _AVAILABLE:
        return _Noop()
    return Gauge(name, doc, labelnames=labels, registry=registry)


class _Noop:
    """Fallback no-op metric used when prometheus_client is unavailable."""

    def labels(self, *_args, **_kwargs) -> _Noop:
        return self

    def inc(self, *_args, **_kwargs) -> None:
        pass

    def observe(self, *_args, **_kwargs) -> None:
        pass

    def set(self, *_args, **_kwargs) -> None:
        pass

    def dec(self, *_args, **_kwargs) -> None:
        pass


# ── HTTP layer ──
http_requests_total = _counter(
    "medagent_http_requests_total",
    "Total HTTP requests received",
    ("method", "path", "status"),
)

http_request_duration_seconds = _histogram(
    "medagent_http_request_duration_seconds",
    "HTTP request latency",
    ("method", "path"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

# ── Agent loop ──
agent_iterations = _histogram(
    "medagent_agent_iterations",
    "Number of ReAct iterations per turn",
    (),
    buckets=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
)

agent_turn_duration_seconds = _histogram(
    "medagent_agent_turn_duration_seconds",
    "Total time for one agent turn",
    ("language",),
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120),
)

agent_turn_total = _counter(
    "medagent_agent_turn_total",
    "Total agent turns",
    ("language", "outcome"),  # outcome: success | error | red_flag
)

# ── Tool calls ──
tool_calls_total = _counter(
    "medagent_tool_calls_total",
    "Total tool invocations",
    ("tool", "outcome"),  # outcome: success | error
)

tool_duration_seconds = _histogram(
    "medagent_tool_duration_seconds",
    "Tool execution time",
    ("tool",),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

# ── Safety / quality ──
red_flags_detected_total = _counter(
    "medagent_red_flags_total",
    "Red flags detected by severity",
    ("severity", "branch"),  # branch: base | pediatric | pregnancy
)

hallucination_score = _histogram(
    "medagent_hallucination_score",
    "Hallucination score from post-LLM gate",
    (),
    buckets=(0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0),
)

triage_level_total = _counter(
    "medagent_triage_level_total",
    "Triage level distribution",
    ("level",),  # emergency | urgent | routine
)

# ── Vision ──
vision_analyses_total = _counter(
    "medagent_vision_analyses_total",
    "Vision tool invocations",
    ("urgency", "is_medical"),
)

# ── LLM ──
llm_tokens_total = _counter(
    "medagent_llm_tokens_total",
    "Tokens consumed by the LLM",
    ("model", "kind"),  # kind: prompt | completion
)

llm_request_seconds = _histogram(
    "medagent_llm_request_seconds",
    "LLM request latency in seconds, by model and operation",
    ("model", "operation"),  # operation: chat | verify | summarize | vision
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

# ── Handoff workflow ──
handoff_transitions_total = _counter(
    "medagent_handoff_transitions_total",
    "Handoff workflow status transitions",
    ("from_status", "to_status"),
)

# ── Active state ──
active_conversations = _gauge(
    "medagent_active_conversations",
    "Conversations currently in 'active' status",
)


@contextmanager
def time_block(metric, *labels: str):
    """Context manager that records elapsed time on a Histogram metric."""
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        with suppress(Exception):
            (metric.labels(*labels) if labels else metric).observe(elapsed)


def render_metrics() -> tuple[bytes, str]:
    """Render the metrics registry to Prometheus text format."""
    if registry is None:
        return generate_latest(), CONTENT_TYPE_LATEST
    return generate_latest(registry), CONTENT_TYPE_LATEST


def _route_template(request: Request) -> str:
    """Return the route template ('/api/v1/handoffs/{handoff_id}') instead of
    the concrete path. Falls back to the literal URL path when Starlette
    couldn't match a route — usually 404s — which is also the only case where
    cardinality from the literal path is safely bounded.
    """
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return route.path
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request latency + count per route/method/status.

    Skips the ``/metrics`` scrape itself to avoid filling dashboards with
    monitoring traffic.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - start

        route = _route_template(request)
        status_label = str(response.status_code)
        with suppress(Exception):
            http_request_duration_seconds.labels(request.method, route).observe(elapsed)
            http_requests_total.labels(request.method, route, status_label).inc()
        return response
