"""Support service: bilingual FAQ + contact ticket creation.

Keeps router thin — all business logic lives here so it can be unit-tested
without spinning up FastAPI.
"""

import uuid

from app.core.database import get_session
from app.models.support_ticket import SupportTicket

# Bilingual FAQ — kept here (not in DB) because it's static content reviewed
# alongside copy changes in messages/{ar,en}.json. Move to DB only when an
# admin needs to edit it without redeploying.
FAQ_ITEMS: list[dict[str, str]] = [
    {
        "q": "What is MedAgent?",
        "a": "MedAgent is a bilingual medical triage AI that helps assess symptoms and guide you to the right care.",
    },
    {
        "q": "Is MedAgent a replacement for a doctor?",
        "a": "No. MedAgent provides preliminary triage only. Always consult a licensed physician for medical decisions.",
    },
    {
        "q": "What languages does MedAgent support?",
        "a": "Arabic and English, including mixed-language conversations.",
    },
    {
        "q": "Is my data private?",
        "a": "Yes. Your conversations are encrypted and only visible to you. We never share your data.",
    },
    {
        "q": "How accurate is the triage?",
        "a": "MedAgent uses evidence-based guidelines but is not 100% accurate. Always follow up with a healthcare professional.",
    },
    {
        "q": "ما هو MedAgent؟",
        "a": "MedAgent هو مساعد فرز طبي ثنائي اللغة يساعد في تقييم الأعراض وتوجيهك للرعاية المناسبة.",
    },
    {
        "q": "هل MedAgent بديل عن الطبيب؟",
        "a": "لا. MedAgent يقدم فرزاً أولياً فقط. استشر طبيباً مرخصاً دائماً للقرارات الطبية.",
    },
]


def list_faq() -> list[dict[str, str]]:
    """Return the static FAQ list."""
    return FAQ_ITEMS


async def submit_contact_ticket(
    *,
    user_id: uuid.UUID | None,
    email: str,
    subject: str,
    message: str,
) -> SupportTicket:
    """Persist a new support ticket. Returns the saved ticket."""
    async with get_session() as session:
        ticket = SupportTicket(
            user_id=user_id,
            email=email,
            subject=subject,
            message=message,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket
