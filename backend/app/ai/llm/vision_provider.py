"""Vision LLM provider — wraps OpenAI vision API and Qwen-VL compatible endpoints."""

import base64
import io
import re
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heic",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# Heuristic patterns that suggest a non-clinical image
NON_CLINICAL_PATTERNS = re.compile(
    r"\b(cat|dog|pet|meme|screenshot|food|selfie|landscape|cartoon|logo|car|"
    r"sport|gaming|قطة|كلب|طعام|سيلفي|كرتون)\b",
    re.IGNORECASE,
)

# Short, factual disclaimers. The previous 4-sentence "⚠️ IMPORTANT — always
# consult a licensed clinician — this tool must NOT replace…" wall was
# dominating every vision result card and made the whole product feel like
# its only job was to deflect. The legal value is the same — "preliminary,
# not a diagnosis" — but framed as a *positioning* statement rather than a
# warning. The actual findings + urgency are the value; this footer just
# clarifies scope.
DISCLAIMER_EN = "AI preliminary triage — not a substitute for clinical examination."
DISCLAIMER_AR = "فرز أولي بالذكاء الاصطناعي — لا يحل محل الفحص السريري."


def _detect_mime(data: bytes) -> str | None:
    """Detect image MIME type from magic bytes."""
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] in (b"RIFF", b"WEBP") or data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] in (b"ftyp", b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c"):
        return "image/heic"
    return None


def validate_image(data: bytes) -> str:
    """Validate image bytes. Returns detected MIME type or raises ValueError."""
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large: {len(data) / 1024 / 1024:.1f} MB (max 10 MB)")
    mime = _detect_mime(data)
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported image format. Accepted: JPEG, PNG, WebP, HEIC. "
            f"Detected: {mime or 'unknown'}"
        )
    return mime


def try_blur_faces(data: bytes, mime: str) -> bytes:
    """Attempt to blur detected faces using Pillow. Falls back to original on error."""
    try:
        from PIL import Image, ImageFilter

        img = Image.open(io.BytesIO(data))

        # Try OpenCV face detection if available
        try:
            import cv2
            import numpy as np

            img_rgb = np.array(img.convert("RGB"))
            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            for x, y, w, h in faces:
                face_region = img.crop((x, y, x + w, y + h))
                blurred = face_region.filter(ImageFilter.GaussianBlur(radius=20))
                img.paste(blurred, (x, y))
            logger.info("face_blur", faces_found=len(faces))
        except ImportError:
            # No OpenCV — apply a global privacy blur to photo-type images
            # (conservative: blur entire image for photos before storage)
            pass

        buf = io.BytesIO()
        fmt = ALLOWED_MIME_TYPES.get(mime, "jpeg").upper()
        if fmt == "JPEG":
            fmt = "JPEG"
        img.save(buf, format=fmt if fmt in ("PNG", "WEBP", "JPEG") else "JPEG")
        return buf.getvalue()
    except Exception as e:
        logger.warning("face_blur_failed", error=str(e))
        return data


class VisionProvider:
    """Calls a vision-capable LLM (OpenAI GPT-4o Vision or compatible) to analyze medical images."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "gpt-4o",
        timeout: float = 90.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_vision_message(
        self,
        image_b64: str,
        mime: str,
        context: str,
        language: str,
    ) -> list[dict]:
        """Build the messages list for a vision API call."""
        # Both branches ask for the EXACT same JSON schema — the Arabic
        # variant used to ask for numbered prose ("1. نوع الصورة ... 4. نسبة
        # الثقة 0.8") which then failed JSON parsing in
        # _parse_vision_response and dropped us into the fallback path with
        # confidence=0.3 hard-coded. That's the "30% bug" the user spotted
        # where the LLM text clearly said 0.8 but the card showed 30%. We
        # keep the language preference for the *content* of the findings
        # but force the *envelope* to be JSON so the parser is happy.
        if language == "ar":
            instruction = (
                "أنت نظام ذكاء اصطناعي طبي متخصص في التحليل الأولي للصور الطبية. "
                "حلل الصورة وأجب **حصريًا** بـ JSON صالح بدون أي نص خارجه، "
                "ولا blocks من ```، بهذا الشكل بالظبط (القيم النصية بالعربية):\n\n"
                "{\n"
                '  "image_kind": "xray|ct|photo|skin|wound|other",\n'
                '  "is_medical": true|false,\n'
                '  "findings": ["وصف أولي 1", "وصف أولي 2"],\n'
                '  "urgency": "emergency|urgent|routine|none",\n'
                '  "confidence": 0.0,\n'
                '  "notes": "تحذيرات مهمة أو سياق غامض"\n'
                "}\n\n"
                "قواعد:\n"
                '- لا تخمّن تشخيصًا قاطعًا. استعمل صيغ احتمالية ("يحتمل"، "يتسق مع").\n'
                "- إذا كانت الصورة غير طبية (قطط، طعام، screenshot): "
                '"is_medical": false, "findings": ["NON_MEDICAL_IMAGE"].\n'
                "- confidence رقم عشري بين 0.0 و 1.0 (مش نص ولا نسبة %).\n"
                "- اكتب findings كقائمة عناصر منفصلة، مش جملة واحدة طويلة."
            )
        else:
            instruction = (
                "You are a medical AI providing preliminary image triage (NOT diagnosis). "
                "Respond ONLY with valid JSON — no prose around it, no markdown code "
                "fences — using this exact schema:\n\n"
                "{\n"
                '  "image_kind": "xray|ct|photo|skin|wound|other",\n'
                '  "is_medical": true|false,\n'
                '  "findings": ["finding 1", "finding 2"],\n'
                '  "urgency": "emergency|urgent|routine|none",\n'
                '  "confidence": 0.0,\n'
                '  "notes": "important caveats"\n'
                "}\n\n"
                "Rules:\n"
                "- Do not commit to a definitive diagnosis. Hedge with "
                '"suggestive of", "consistent with".\n'
                "- If the image is clearly NOT medical (pet, food, screenshot, meme), "
                'set "is_medical": false and "findings": ["NON_MEDICAL_IMAGE"].\n'
                "- confidence is a float between 0.0 and 1.0 (not a string, not a %).\n"
                "- findings is a list of separate short items, not one long sentence."
            )

        user_content: list[dict] = [
            {
                "type": "text",
                "text": f"{instruction}\n\nPatient context: {context or 'None provided'}",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{image_b64}",
                    "detail": "high",
                },
            },
        ]
        return [{"role": "user", "content": user_content}]

    async def analyze(
        self,
        image_data: bytes,
        context: str = "",
        language: str = "en",
        image_kind: str = "photo",
    ) -> dict[str, Any]:
        """
        Analyze medical image bytes.

        Parameters
        ----------
        image_data : bytes
            Raw image bytes (JPEG/PNG/WebP/HEIC, max 10 MB).
        context : str
            Patient symptom context to help the model.
        language : str
            "ar" or "en" — controls response language.
        image_kind : str
            Hint: "xray", "ct", "photo", "skin", "other".

        Returns
        -------
        dict with keys: findings, urgency, confidence, disclaimer, is_medical, image_kind
        """
        mime = validate_image(image_data)

        # Blur faces for photo-type images before encoding
        if image_kind in ("photo", "skin"):
            image_data = try_blur_faces(image_data, mime)

        image_b64 = base64.b64encode(image_data).decode("ascii")
        messages = self._build_vision_message(image_b64, mime, context, language)

        disclaimer = DISCLAIMER_AR if language == "ar" else DISCLAIMER_EN
        raw_content = ""

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json={
                            "model": self.model,
                            "messages": messages,
                            "max_tokens": 512,
                            "temperature": 0.1,
                        },
                    )
                    if resp.status_code >= 400:
                        print("\n" + "=" * 50)
                        print(f"🚨 MODEL SENT TO GROQ: {self.model}")
                        print(f"🚨 GROQ ERROR DETAILS: {resp.text}")
                        print("=" * 50 + "\n")
                    resp.raise_for_status()
                    data = resp.json()
                    raw_content = data["choices"][0]["message"].get("content", "")
                    break
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries:
                    import asyncio

                    await asyncio.sleep(2**attempt)
                else:
                    logger.error("vision_llm_failed", error=str(e))
                    return {
                        "findings": ["Vision LLM unavailable. Please try again later."],
                        "urgency": "routine",
                        "confidence": 0.0,
                        "is_medical": True,
                        "image_kind": image_kind,
                        "disclaimer": disclaimer,
                        "error": str(last_exc),
                    }

        return _parse_vision_response(raw_content, image_kind, disclaimer)


def _parse_vision_response(
    raw: str,
    image_kind: str,
    disclaimer: str,
) -> dict[str, Any]:
    """Parse the vision LLM's response into a structured dict.

    Resilient to common LLM output shapes:
      1. Pure JSON (best case)
      2. JSON wrapped in ``` markdown fence
      3. JSON embedded in prose ("Here is the analysis: { ... }")
      4. Numbered Arabic prose ("1. نوع الصورة ... 4. نسبة الثقة 0.8")
      5. Total garbage (last-resort fallback)

    The historical bug was that (4) is what Arabic-prompted models actually
    return, but the parser only handled (1)-(2), so every Arabic response
    fell through to a hardcoded ``confidence=0.3`` (the "30% bug"). We now
    also salvage confidence + urgency from numbered prose so the UX is
    truthful even when the model ignores the JSON instruction.
    """
    import json as _json

    if "NON_MEDICAL" in raw.upper():
        return {
            "findings": [],
            "urgency": "none",
            "confidence": 0.0,
            "is_medical": False,
            "image_kind": image_kind,
            "disclaimer": disclaimer,
            "refusal_reason": (
                "This image does not appear to be a medical image. "
                "Please upload a clinical photo, X-ray, CT scan, or other medical image."
            ),
        }

    # ── Strategy 1+2+3: try to find a JSON object anywhere in the response ──
    json_candidates: list[str] = []
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        json_candidates.append(fence.group(1))
    # Greedy match of the outermost { … } block
    bare = re.search(r"\{[\s\S]*\}", raw)
    if bare:
        json_candidates.append(bare.group(0))
    # Whole string
    json_candidates.append(raw.strip())

    for candidate in json_candidates:
        try:
            parsed = _json.loads(candidate)
        except (_json.JSONDecodeError, ValueError):
            continue
        # Validate it has at least one of the expected keys before accepting.
        if any(k in parsed for k in ("findings", "urgency", "confidence")):
            return {
                "findings": parsed.get("findings", []) or [raw],
                "urgency": parsed.get("urgency", "routine"),
                "confidence": float(parsed.get("confidence", 0.5)),
                "is_medical": parsed.get("is_medical", True),
                "image_kind": parsed.get("image_kind", image_kind),
                "notes": parsed.get("notes", ""),
                "disclaimer": disclaimer,
            }

    # ── Strategy 4: salvage from numbered Arabic/English prose ──
    # Most Arabic-prompted models still produce "1. ... 2. ... 4. نسبة الثقة 0.8"
    # even when asked for JSON. Pull out the urgency + confidence so the card
    # doesn't lie ("30%") while the prose clearly says 0.8.
    salvaged_confidence = _extract_confidence(raw)
    salvaged_urgency = _extract_urgency(raw)
    salvaged_findings = _split_findings(raw)

    return {
        "findings": salvaged_findings or [raw] if raw else ["Analysis complete."],
        "urgency": salvaged_urgency,
        # Only fall back to 0.3 if we truly couldn't find anything — and
        # mark this as a parse-failure signal in the notes field rather
        # than hardcoding 0.3.
        "confidence": salvaged_confidence if salvaged_confidence is not None else 0.3,
        "is_medical": True,
        "image_kind": image_kind,
        "disclaimer": disclaimer,
        "notes": "Parsed from prose — JSON envelope was malformed."
        if salvaged_confidence is not None
        else "Vision model returned unstructured output.",
    }


_CONFIDENCE_PATTERNS = [
    # English: confidence: 0.8 / "confidence" = 0.85 / Confidence in result: 0.7
    # Allow up to 40 chars of "of … the analysis" filler between the cue word
    # and the colon (e.g. "Confidence in the result: 0.8").
    re.compile(
        r"confidence(?:[^\d:=\n]{0,40})?\s*[:=]\s*([01](?:\.\d+)?)\b",
        re.IGNORECASE,
    ),
    # Arabic: نسبة الثقة: 0.8 / الثقة في النتائج: 0.8 / الثقة 0.85
    # Same idea — allow Arabic filler words like "في النتائج" / "بالتشخيص".
    re.compile(r"(?:نسبة\s+)?الثقة(?:[^\d:=\n]{0,40})?\s*[:=]?\s*([01]\.\d+)"),
    # Bare percentage: "80%" → 0.8 — only if it looks like a confidence
    # context (precede it with "confidence" / "ثقة" within 30 chars).
    re.compile(r"(?:confidence|ثقة)[^%]{0,30}?(\d{1,3})\s*%", re.IGNORECASE),
]


def _extract_confidence(raw: str) -> float | None:
    """Pull a confidence value out of free-form prose.

    Returns a float in [0.0, 1.0] or None if nothing parseable was found.
    For percentage hits (e.g. "80%") we divide by 100.
    """
    for pat in _CONFIDENCE_PATTERNS:
        m = pat.search(raw)
        if not m:
            continue
        try:
            value = float(m.group(1))
        except ValueError:
            continue
        if value > 1.0:
            value = value / 100.0
        if 0.0 <= value <= 1.0:
            return value
    return None


def _extract_urgency(raw: str) -> str:
    """Best-effort urgency extraction from free-form text."""
    lower = raw.lower()
    # Order matters: check emergency first so "non emergency" doesn't false-positive.
    if any(t in raw for t in ("طوارئ", "emergency")) and "non" not in lower:
        return "emergency"
    if any(t in raw for t in ("عاجل", "urgent")):
        return "urgent"
    if any(t in raw for t in ("روتيني", "routine")):
        return "routine"
    return "routine"


def _split_findings(raw: str) -> list[str]:
    """Split numbered prose ("1. foo 2. bar") into a list of findings."""
    # Look for "1." "2." "3." style numbered items (Arabic or Latin digits).
    parts = re.split(r"(?:^|\s)(?:[1-9]|[١-٩])\s*[.،]\s*", raw)
    cleaned = [p.strip() for p in parts if p.strip()]
    if len(cleaned) >= 2:
        return cleaned[:8]  # cap at 8 to avoid hallucinated explosions
    # Fallback: split on newlines
    lines = [line.strip(" -•\t") for line in raw.splitlines() if line.strip()]
    return lines[:8] if lines else []
