"""Support router — FAQ + contact form. Thin HTTP layer over service.py."""

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.modules.support.service import list_faq, submit_contact_ticket

support_router = APIRouter(prefix="/support", tags=["support"])


@support_router.get("/faq")
async def get_faq():
    """List FAQ items."""
    return {"items": list_faq()}


@support_router.post("/contact", status_code=201)
async def submit_contact(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Submit a contact/support form."""
    user_id = uuid.UUID(current_user["sub"]) if current_user else None
    ticket = await submit_contact_ticket(
        user_id=user_id,
        email=body.get("email", ""),
        subject=body.get("subject", ""),
        message=body.get("message", ""),
    )
    return {"ticket_id": str(ticket.id)}
