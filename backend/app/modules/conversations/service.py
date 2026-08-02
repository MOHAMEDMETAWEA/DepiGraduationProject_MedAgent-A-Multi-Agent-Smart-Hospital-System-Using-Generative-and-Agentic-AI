"""Conversation service: CRUD + agent chat integration."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.common.audit import log_action
from app.core.database import get_session
from app.models.conversation import Conversation
from app.models.messages import Message


async def create_conversation(
    user_id: uuid.UUID,
    language: str = "ar",
) -> Conversation:
    """Create a new conversation for a patient."""
    async with get_session() as session:
        conv = Conversation(
            patient_user_id=user_id,
            language=language,
            status="active",
        )
        session.add(conv)
        await session.commit()
        log_action(
            "create_conversation",
            user_id=user_id,
            resource_type="conversation",
            resource_id=conv.id,
        )
        return conv


async def get_conversation(conv_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
    """Get a conversation by ID, ensuring it belongs to the user."""
    async with get_session() as session:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.patient_user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


async def list_conversations(
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[Conversation], int]:
    """List conversations for a user with pagination and optional status filter."""
    async with get_session() as session:
        query = select(Conversation).where(Conversation.patient_user_id == user_id)
        count_query = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.patient_user_id == user_id)
        )

        if status:
            query = query.where(Conversation.status == status)
            count_query = count_query.where(Conversation.status == status)
        else:
            # Exclude deleted conversations by default
            query = query.where(Conversation.status != "deleted")
            count_query = count_query.where(Conversation.status != "deleted")

        query = query.order_by(Conversation.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        convs = list(result.scalars().all())

        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        return convs, total


async def delete_conversation(conv_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Soft-delete by marking status='deleted'."""
    async with get_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv or conv.patient_user_id != user_id:
            return False
        conv.status = "deleted"
        await session.commit()
        log_action(
            "delete_conversation",
            user_id=user_id,
            resource_type="conversation",
            resource_id=conv_id,
        )
        return True


async def get_messages(conv_id: uuid.UUID) -> list[Message]:
    """Get all messages for a conversation, ordered by time."""
    async with get_session() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())


async def add_message(
    conv_id: uuid.UUID,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    tool_calls: list[dict] | None = None,
    tool_name: str | None = None,
    metadata: dict | None = None,
) -> Message:
    """Add a message to a conversation. PHI body is encrypted at rest when enabled."""
    async with get_session() as session:
        msg = Message.from_payload(
            conversation_id=conv_id,
            role=role,
            content=content,
            citations=citations or [],
            tool_calls=tool_calls or [],
            tool_name=tool_name,
            extra_meta=metadata,
        )
        session.add(msg)

        # Update conversation timestamp. Title preview uses the first 100 chars of the
        # user-visible text — this is metadata, not PHI body, so left unencrypted.
        conv = await session.get(Conversation, conv_id)
        if conv:
            if not conv.title:
                conv.title = content[:100] if role == "user" else conv.title
            conv.updated_at = datetime.now(UTC)

        await session.commit()
        return msg


async def update_triage(
    conv_id: uuid.UUID,
    level: str,
    score: int | None = None,
    red_flags: list[dict] | None = None,
    set_flagged: bool = False,
) -> None:
    """Update triage info on a conversation."""
    async with get_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv:
            return
        conv.triage_level = level
        if score is not None:
            conv.triage_score = score
        if red_flags is not None:
            conv.red_flags_detected = red_flags
        if set_flagged:
            conv.status = "flagged_for_review"
        await session.commit()

    if set_flagged and red_flags and len(red_flags) > 0:
        from app.modules.notifications.service import schedule_safety_follow_up

        await schedule_safety_follow_up(conversation_id=conv_id)


async def complete_conversation(conv_id: uuid.UUID) -> None:
    """Mark a conversation as completed and schedule follow-up notifications."""
    async with get_session() as session:
        conv = await session.get(Conversation, conv_id)
        if conv:
            conv.status = "completed"
            conv.completed_at = datetime.now(UTC)
            await session.commit()

    from app.modules.notifications.service import FOLLOW_UP_DELAYS, schedule_follow_up

    async with get_session() as session:
        conv = await session.get(Conversation, conv_id)
        if conv and conv.triage_level in FOLLOW_UP_DELAYS:
            await schedule_follow_up(
                conversation_id=conv_id,
                delay_hours=FOLLOW_UP_DELAYS[conv.triage_level],
                template="follow_up",
            )


def to_response(conv: Conversation, messages: list[Message] | None = None) -> dict:
    """Convert Conversation ORM object to API response dict."""
    msg_list = messages or []
    last_msg = msg_list[-1].text[:80] if msg_list else None

    return {
        "id": str(conv.id),
        "title": conv.title,
        "status": conv.status,
        "triage_level": conv.triage_level,
        "triage_score": conv.triage_score,
        "language": conv.language,
        "red_flags_detected": conv.red_flags_detected,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": len(msg_list) if messages is not None else 0,
        "last_message": last_msg,
    }
