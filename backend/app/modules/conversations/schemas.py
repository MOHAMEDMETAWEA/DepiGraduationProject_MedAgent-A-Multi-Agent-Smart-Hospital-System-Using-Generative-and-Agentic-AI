"""Pydantic schemas for conversations and messages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Message ──


class MessageResponse(BaseModel):
    """A single message in a conversation."""

    id: uuid.UUID
    role: str  # "user", "assistant", "tool", "system"
    content: str
    citations: list[dict] = []
    tool_calls: list[dict] = []
    tool_name: str | None = None
    created_at: datetime


# ── Conversation ──


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""

    language: str = Field(default="ar", pattern="^(ar|en)$")


class ConversationResponse(BaseModel):
    """Conversation details returned to the client."""

    id: uuid.UUID
    title: str | None = None
    status: str  # "active", "flagged_for_review", "completed"
    triage_level: str | None = None  # "emergency", "urgent", "routine"
    triage_score: int | None = None
    language: str
    red_flags_detected: list[dict] = []
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: str | None = None  # snippet for preview


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    items: list[ConversationResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ── Chat ──


class ChatRequest(BaseModel):
    """Send a message and get agent response."""

    message: str = Field(..., min_length=1)
    model: str | None = Field(
        default=None,
        description="LLM model override (e.g. openai/gpt-4o, qwen/qwen-2.5-72b-instruct)",
    )
    image_data: str | None = Field(
        default=None,
        description=(
            "Optional base64 data URI of an attached medical image "
            "(e.g. 'data:image/png;base64,...'). Triggers analyze_vision tool."
        ),
    )
    image_kind: str | None = Field(
        default=None,
        description="Optional hint about image type: xray | ct | photo | skin | wound | other",
    )
    # ── Per-request vision provider override ──
    # Lets the frontend A/B-test vision models without touching .env.
    # When unset, _create_vision_provider() picks the configured default.
    vision_provider: str | None = Field(
        default=None,
        description="Override vision backend for this request: gemini | groq | openai | openrouter",
    )
    vision_model: str | None = Field(
        default=None,
        description="Override the model id sent to the chosen vision backend.",
    )


class ChatEvent(BaseModel):
    """Streaming event sent via SSE."""

    type: str  # "token", "tool_start", "tool_result", "triage", "red_flag", "done", "error"
    content: str = ""
    data: dict = {}
