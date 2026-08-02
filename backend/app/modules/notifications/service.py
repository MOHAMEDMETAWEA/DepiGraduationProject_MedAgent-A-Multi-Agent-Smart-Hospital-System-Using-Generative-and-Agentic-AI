import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import get_session
from app.core.email import send_email
from app.core.logging import get_logger
from app.models.conversation import Conversation
from app.models.notification_log import NotificationLog
from app.models.users import User

logger = get_logger(__name__)

FOLLOW_UP_DELAYS = {
    "emergency": 6,
    "urgent": 12,
    "routine": 72,
}

SAFETY_FOLLOW_UP_DELAY = 24


def _build_follow_up_html(
    user_name: str,
    template: str,
    language: str,
    triage_level: str | None = None,
    conversation_title: str | None = None,
    reason: str | None = None,
) -> tuple[str, str]:
    """Build bilingual follow-up email HTML and subject."""
    if template == "safety_follow_up":
        subject = "تذكير متابعة طبية عاجلة | Urgent Medical Follow-Up Reminder"
        body_ar = f"""
        <div dir="rtl" style="font-family: Tahoma, sans-serif;">
            <h2>مرحباً {user_name}،</h2>
            <p>هذا تذكير من <strong>MedAgent</strong> بخصوص استشارتك الطبية الأخيرة.</p>
            <p>نظراً لوجود <strong>علامات تحذيرية (Red Flags)</strong> في تقييمك، نوصي بشدة بالمتابعة مع طبيب مختص في أقرب وقت.</p>
            <p style="color: #d32f2f; font-weight: bold;">لا تتجاهل هذه الأعراض — صحتك أهم شيء.</p>
            <p>إذا كنت قد راجعت طبيباً بالفعل، يمكنك تجاهل هذه الرسالة.</p>
            <hr />
            <p style="color: #888; font-size: 14px;">هذه رسالة آلية من نظام MedAgent للفرز الطبي. لا ترد على هذا البريد.</p>
        </div>
        """
        body_en = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>Hello {user_name},</h2>
            <p>This is a reminder from <strong>MedAgent</strong> regarding your recent medical consultation.</p>
            <p>Due to <strong>warning signs (Red Flags)</strong> detected in your assessment, we strongly recommend following up with a specialist as soon as possible.</p>
            <p style="color: #d32f2f; font-weight: bold;">Do not ignore these symptoms — your health matters.</p>
            <p>If you have already seen a doctor, you may disregard this message.</p>
            <hr />
            <p style="color: #888; font-size: 14px;">This is an automated message from MedAgent triage system. Do not reply to this email.</p>
        </div>
        """
        body = body_ar + "<br/><br/>" + body_en

    elif template == "follow_up":
        triage_labels = {
            "emergency": ("طارئ", "Emergency"),
            "urgent": ("عاجل", "Urgent"),
            "routine": ("روتيني", "Routine"),
        }
        label_ar, label_en = triage_labels.get(triage_level or "routine", ("روتيني", "Routine"))

        subject = "متابعة استشارة طبية | Medical Consultation Follow-Up"
        reason_text_ar = f"<p>السبب: {reason}</p>" if reason else ""
        reason_text_en = f"<p>Reason: {reason}</p>" if reason else ""
        title_text_ar = f"<p>الاستشارة: {conversation_title}</p>" if conversation_title else ""
        title_text_en = f"<p>Consultation: {conversation_title}</p>" if conversation_title else ""

        body_ar = f"""
        <div dir="rtl" style="font-family: Tahoma, sans-serif;">
            <h2>مرحباً {user_name}،</h2>
            <p>نأمل أن تكون بصحة جيدة. هذه متابعة من <strong>MedAgent</strong> بعد استشارتك الطبية الأخيرة.</p>
            <p>مستوى الفرز: <strong>{label_ar}</strong></p>
            {title_text_ar}
            {reason_text_ar}
            <p>إذا استمرت الأعراض أو تفاقمت، ننصحك بمراجعة طبيب مختص.</p>
            <hr />
            <p style="color: #888; font-size: 14px;">هذه رسالة آلية من نظام MedAgent. لا ترد على هذا البريد.</p>
        </div>
        """
        body_en = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>Hello {user_name},</h2>
            <p>We hope you are doing well. This is a follow-up from <strong>MedAgent</strong> after your recent consultation.</p>
            <p>Triage Level: <strong>{label_en}</strong></p>
            {title_text_en}
            {reason_text_en}
            <p>If your symptoms persist or worsen, we recommend seeing a specialist.</p>
            <hr />
            <p style="color: #888; font-size: 14px;">This is an automated message from MedAgent. Do not reply to this email.</p>
        </div>
        """
        body = body_ar + "<br/><br/>" + body_en
    else:
        subject = "MedAgent Notification"
        body = f"<p>Notification for {user_name}</p>"

    return body, subject


async def schedule_notification(
    user_id: uuid.UUID,
    recipient: str,
    channel: str,
    template: str,
    scheduled_for: datetime,
    metadata: dict | None = None,
) -> uuid.UUID:
    """Insert a queued notification and return its ID."""
    meta = metadata or {}
    meta["scheduled_for"] = scheduled_for.isoformat()

    notification = NotificationLog(
        user_id=user_id,
        channel=channel,
        template=template,
        recipient=recipient,
        status="queued",
        extra_meta=meta,
    )

    async with get_session() as session:
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification.id


async def schedule_follow_up(
    conversation_id: uuid.UUID,
    delay_hours: int = 24,
    template: str = "follow_up",
    reason: str | None = None,
) -> uuid.UUID | None:
    """Schedule a follow-up notification for a conversation."""
    async with get_session() as session:
        conv = await session.get(Conversation, conversation_id)
        if not conv:
            return None

        user = await session.get(User, conv.patient_user_id)
        if not user:
            return None

    scheduled_for = datetime.now(UTC) + timedelta(hours=delay_hours)

    return await schedule_notification(
        user_id=user.id,
        recipient=user.email,
        channel="email",
        template=template,
        scheduled_for=scheduled_for,
        metadata={
            "conversation_id": str(conversation_id),
            "triage_level": conv.triage_level,
            "reason": reason,
            "language": user.locale,
            "user_name": user.full_name,
        },
    )


async def schedule_safety_follow_up(
    conversation_id: uuid.UUID,
    delay_hours: int = SAFETY_FOLLOW_UP_DELAY,
) -> uuid.UUID | None:
    """Schedule a safety follow-up notification (red flags detected)."""
    return await schedule_follow_up(
        conversation_id=conversation_id,
        delay_hours=delay_hours,
        template="safety_follow_up",
        reason="تم اكتشاف علامات تحذيرية | Red flags detected",
    )


async def schedule_auto_follow_ups(conversation_id: uuid.UUID) -> list[uuid.UUID]:
    """Automatically schedule follow-up notifications based on triage level and red flags.

    Called when a conversation is completed or when red flags are detected mid-conversation.
    Returns list of created notification IDs.
    """
    async with get_session() as session:
        conv = await session.get(Conversation, conversation_id)
        if not conv:
            return []

    notification_ids: list[uuid.UUID] = []

    # Safety follow-up if red flags exist
    if conv.red_flags_detected and len(conv.red_flags_detected) > 0:
        safety_id = await schedule_safety_follow_up(
            conversation_id=conversation_id,
            delay_hours=SAFETY_FOLLOW_UP_DELAY,
        )
        if safety_id:
            notification_ids.append(safety_id)
            logger.info(
                "safety_follow_up_scheduled",
                conversation_id=str(conversation_id),
                notification_id=str(safety_id),
            )

    # Regular follow-up for emergency and urgent
    if conv.triage_level in FOLLOW_UP_DELAYS:
        delay = FOLLOW_UP_DELAYS[conv.triage_level]
        follow_up_id = await schedule_follow_up(
            conversation_id=conversation_id,
            delay_hours=delay,
            template="follow_up",
        )
        if follow_up_id:
            notification_ids.append(follow_up_id)
            logger.info(
                "follow_up_scheduled",
                conversation_id=str(conversation_id),
                triage_level=conv.triage_level,
                delay_hours=delay,
                notification_id=str(follow_up_id),
            )

    return notification_ids


async def process_due_notifications() -> dict:
    """Process all due queued notifications. Intended to run as a background task.

    Returns {"processed": N, "sent": N, "failed": N}.
    """
    now = datetime.now(UTC)
    processed = 0
    sent = 0
    failed = 0

    async with get_session() as session:
        result = await session.execute(
            select(NotificationLog).where(NotificationLog.status == "queued")
        )
        queued = result.scalars().all()

        for notification in queued:
            meta = notification.extra_meta or {}
            scheduled_for_str = meta.get("scheduled_for")

            if not scheduled_for_str:
                continue

            try:
                scheduled_for = datetime.fromisoformat(scheduled_for_str)
            except (ValueError, TypeError):
                continue

            if scheduled_for > now:
                continue  # Not yet due

            processed += 1

            # Build email
            user_name = meta.get("user_name", "Patient")
            language = meta.get("language", "ar")
            triage_level = meta.get("triage_level")
            conversation_title = meta.get("conversation_title")
            reason = meta.get("reason")

            html_body, subject = _build_follow_up_html(
                user_name=user_name,
                template=notification.template,
                language=language,
                triage_level=triage_level,
                conversation_title=conversation_title,
                reason=reason,
            )

            success = await send_email(
                to=notification.recipient,
                subject=subject,
                html_body=html_body,
            )

            if success:
                notification.status = "sent"
                notification.sent_at = now
                sent += 1
                logger.info(
                    "notification_sent",
                    notification_id=str(notification.id),
                    template=notification.template,
                )
            else:
                notification.status = "failed"
                notification.error_message = "SMTP send failed"
                failed += 1
                logger.error(
                    "notification_failed",
                    notification_id=str(notification.id),
                    template=notification.template,
                )

        await session.commit()

    return {"processed": processed, "sent": sent, "failed": failed}


async def get_user_notifications(
    user_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> tuple[list[NotificationLog], int]:
    """Get paginated notifications for a user."""
    async with get_session() as session:
        total_result = await session.execute(
            select(NotificationLog).where(NotificationLog.user_id == user_id)
        )
        total = len(total_result.scalars().all())

        result = await session.execute(
            select(NotificationLog)
            .where(NotificationLog.user_id == user_id)
            .order_by(NotificationLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        notifications = result.scalars().all()

        return list(notifications), total
