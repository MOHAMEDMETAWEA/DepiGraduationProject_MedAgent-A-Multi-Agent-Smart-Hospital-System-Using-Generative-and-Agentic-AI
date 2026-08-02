"""Conversation API router: CRUD + SSE streaming chat."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.modules.conversations.schemas import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
)
from app.modules.conversations.service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_messages,
    list_conversations,
    to_response,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create(body: ConversationCreate, current_user: dict = Depends(get_current_user)):
    """Create a new conversation."""
    conv = await create_conversation(
        user_id=uuid.UUID(current_user["sub"]),
        language=body.language,
    )
    return to_response(conv)


@router.get("", response_model=ConversationListResponse)
async def list_convs(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """List conversations for the current user."""
    convs, total = await list_conversations(
        user_id=uuid.UUID(current_user["sub"]),
        page=page,
        page_size=page_size,
        status=status,
    )
    items = [to_response(c) for c in convs]
    return ConversationListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conv(conv_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    """Get a single conversation with its message count."""
    conv = await get_conversation(conv_id, uuid.UUID(current_user["sub"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_messages(conv_id)
    return to_response(conv, messages)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conv(conv_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    """Soft-delete a conversation."""
    ok = await delete_conversation(conv_id, uuid.UUID(current_user["sub"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/{conv_id}/messages")
async def list_messages(conv_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    """Get all messages for a conversation. Decrypts PHI body in-flight.

    Also surfaces persisted streaming events (`events` in extra_meta) so the
    frontend can re-render the same triage badge / watch signals / ToT panel
    when a user navigates back to an older conversation.
    """
    conv = await get_conversation(conv_id, uuid.UUID(current_user["sub"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_messages(conv_id)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.text,
            "citations": m.citations,
            "tool_calls": m.tool_calls,
            "tool_name": m.tool_name,
            "events": (m.extra_meta or {}).get("events", []),
            # Attached image so the chat can re-show the picture on reload.
            # Only ever set on user messages where the patient attached one.
            "image_data": (m.extra_meta or {}).get("image_data"),
            "image_kind": (m.extra_meta or {}).get("image_kind"),
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.get("/{conv_id}/triage")
async def get_triage(conv_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    """Get triage assessment for a conversation."""
    conv = await get_conversation(conv_id, uuid.UUID(current_user["sub"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "level": conv.triage_level,
        "score": conv.triage_score,
        "red_flags": conv.red_flags_detected,
    }
