"""Tool: analyze_vision — preliminary medical image triage via vision LLM."""

import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent.base import Tool
from app.ai.llm.vision_provider import (
    DISCLAIMER_AR,
    DISCLAIMER_EN,
    MAX_IMAGE_BYTES,
    VisionProvider,
    validate_image,
)

ALLOWED_IMAGE_KINDS = frozenset({"xray", "ct", "photo", "skin", "wound", "other"})


class VisionInput(BaseModel):
    """Input schema for vision analysis tool."""

    image_url: str = Field(
        ...,
        min_length=1,
        description=(
            "URL (http/https) or base64 data URI of the medical image to analyze. "
            "Accepted formats: JPEG, PNG, WebP, HEIC. Max size: 10 MB."
        ),
    )
    image_kind: str = Field(
        default="other",
        description="Type of image: xray | ct | photo | skin | wound | other",
    )
    context: str = Field(
        default="",
        max_length=2000,
        description="Patient context — symptoms, history, reason for uploading the image",
    )
    language: str = Field(
        default="en",
        pattern="^(ar|en)$",
        description="Response language: ar (Arabic) or en (English)",
    )
    conversation_id: str = Field(
        default="",
        description="UUID of the current conversation (for DB recording)",
    )


class AnalyzeVisionTool(Tool):
    """Preliminary medical image triage using a vision-capable LLM.

    Accepts JPEG/PNG/WebP/HEIC up to 10 MB. Refuses non-clinical images.
    Always returns a disclaimer. Records in vision_analyses table.
    """

    def __init__(
        self,
        vision_provider: VisionProvider | None = None,
        db_session: AsyncSession | None = None,
    ):
        self._vision: VisionProvider | None = vision_provider
        self._db: AsyncSession | None = db_session

    def set_vision_provider(self, provider: VisionProvider) -> None:
        self._vision = provider

    def set_db_session(self, session: AsyncSession) -> None:
        self._db = session

    @property
    def name(self) -> str:
        return "analyze_vision"

    @property
    def description(self) -> str:
        return (
            "Analyze a medical image (skin condition, wound, rash, X-ray, CT) "
            "and return preliminary findings, urgency assessment (emergency/urgent/routine), "
            "confidence score, and a mandatory medical disclaimer. "
            "Refuses non-medical images (pets, food, screenshots). "
            "This is preliminary triage only — NOT a diagnosis."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return VisionInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, VisionInput):
            raise TypeError(f"Expected VisionInput, got {type(input_data)}")

        disclaimer = DISCLAIMER_AR if input_data.language == "ar" else DISCLAIMER_EN

        # Validate image_kind
        kind = input_data.image_kind.lower()
        if kind not in ALLOWED_IMAGE_KINDS:
            kind = "other"

        # ── Fetch + validate image bytes ──
        image_data, fetch_error = await _fetch_image(input_data.image_url)
        if fetch_error:
            return {
                "findings": [],
                "urgency": "routine",
                "confidence": 0.0,
                "is_medical": False,
                "image_kind": kind,
                "disclaimer": disclaimer,
                "error": fetch_error,
            }

        try:
            validate_image(image_data)
        except ValueError as e:
            return {
                "findings": [],
                "urgency": "routine",
                "confidence": 0.0,
                "is_medical": False,
                "image_kind": kind,
                "disclaimer": disclaimer,
                "error": str(e),
            }

        # ── Run vision LLM ──
        if self._vision is None:
            result: dict[str, Any] = {
                "findings": ["Vision analysis requires a configured vision LLM provider."],
                "urgency": "routine",
                "confidence": 0.0,
                "is_medical": True,
                "image_kind": kind,
                "disclaimer": disclaimer,
            }
        else:
            result = await self._vision.analyze(
                image_data=image_data,
                context=input_data.context,
                language=input_data.language,
                image_kind=kind,
            )

        # ── Persist to vision_analyses table ──
        if self._db and input_data.conversation_id:
            await _save_to_db(
                session=self._db,
                conversation_id=input_data.conversation_id,
                image_url=input_data.image_url,
                image_kind=kind,
                result=result,
                model=getattr(self._vision, "model", None) if self._vision else None,
            )

        # Ensure disclaimer is always present
        result["disclaimer"] = disclaimer
        return result


def _is_private_or_blocked_ip(host: str) -> bool:
    """Phase E (E3): return True if the host resolves to a non-public IP.

    Blocks SSRF vectors:
    - RFC1918 (10/8, 172.16/12, 192.168/16)
    - 127/8 (loopback)
    - 169.254/16 (link-local — cloud metadata at 169.254.169.254!)
    - 100.64/10 (CGNAT)
    - 0.0.0.0/8 (this network)
    - IPv6 loopback / link-local / unique-local
    """
    import ipaddress
    import socket

    try:
        # Resolve all A/AAAA records — a malicious DNS could return one safe +
        # one private IP, so we have to reject if ANY result is bad.
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return True
        return False
    except (socket.gaierror, ValueError):
        # If we can't resolve the host, refuse to fetch it.
        return True


async def _fetch_image(image_url: str) -> tuple[bytes, str | None]:
    """Fetch image bytes from a URL or decode a base64 data URI.

    Implements SSRF defense (E3): refuses non-http(s) schemes, resolves the
    host before issuing the request, and rejects any address inside private
    or otherwise sensitive ranges. ``follow_redirects`` is disabled so a
    302 to ``169.254.169.254`` can't bypass the check.
    """
    if image_url.startswith("data:"):
        # data:image/jpeg;base64,/9j/...
        try:
            import base64

            _header, b64 = image_url.split(",", 1)
            data = base64.b64decode(b64)
            if len(data) > MAX_IMAGE_BYTES:
                return b"", f"Image too large: {len(data) / 1024 / 1024:.1f} MB (max 10 MB)"
            return data, None
        except Exception as e:
            return b"", f"Invalid base64 image data: {e}"

    if image_url.startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse

            import httpx

            parsed = urlparse(image_url)
            if not parsed.hostname:
                return b"", "image_url has no host"

            # E3: hard-block private / loopback / metadata IPs.
            if _is_private_or_blocked_ip(parsed.hostname):
                return b"", "image_url resolves to a private or restricted address"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(image_url, follow_redirects=False)
                # If the server redirects, refuse rather than chase — a
                # redirect could otherwise bypass the IP allow-list.
                if 300 <= resp.status_code < 400:
                    return b"", "image_url returned a redirect (refused)"
                resp.raise_for_status()
                data = resp.content
                if len(data) > MAX_IMAGE_BYTES:
                    return b"", f"Image too large: {len(data) / 1024 / 1024:.1f} MB (max 10 MB)"
                return data, None
        except Exception as e:
            return b"", f"Could not fetch image: {e}"

    return b"", "image_url must be an http/https URL or a base64 data URI"


async def _save_to_db(
    session: AsyncSession,
    conversation_id: str,
    image_url: str,
    image_kind: str,
    result: dict[str, Any],
    model: str | None,
) -> None:
    """Persist vision analysis record. Silently swallows errors to never block the tool."""
    try:
        from app.models.vision_analysis import VisionAnalysis

        findings = result.get("findings", [])
        urgency = result.get("urgency", "routine")
        confidence = result.get("confidence")
        analysis_md = "\n".join(str(f) for f in findings) if findings else None

        record = VisionAnalysis(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            image_url=image_url[:500],
            image_kind=image_kind,
            analysis_markdown=analysis_md,
            findings={"findings": findings, "notes": result.get("notes", "")},
            urgency=urgency,
            confidence=float(confidence) if confidence is not None else None,
            model_used=model,
            disclaimer_shown=True,
        )
        session.add(record)
        await session.commit()
    except Exception as e:
        import structlog

        structlog.get_logger(__name__).warning("vision_db_save_failed", error=str(e))
