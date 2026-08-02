"""PII scrubbing utility — removes personal identifiers from text before LLM."""

import re

# Egyptian phone numbers: 01xxxxxxxxx, +201xxxxxxxxx
_PHONE_RE = re.compile(r"(\+?2\s?0?)?1[0125]\d{8}")
# Email patterns
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# National ID (14 digits)
_NATIONAL_ID_RE = re.compile(r"\b[23]\d{13}\b")
# Name patterns — only when explicitly introducing oneself
_NAME_PATTERNS = [
    r"(?:اسمي|my name is)\s+([A-Za-z\u0600-\u06FF\s]{2,30})",
]
# Address — only match explicit address patterns with numbers or street names
_ADDRESS_PATTERNS = [
    r"\d+\s+(?:شارع|street|st\.?|road|rd\.?|avenue|ave\.?)[\s,]+[A-Za-z\u0600-\u06FF\s]+",
]


def scrub_pii(text: str) -> str:
    """Remove or mask personally identifiable information from text.

    Masks: phone numbers, emails, national IDs, and explicit name/address
    introductions. Returns cleaned text safe for LLM input.
    """
    if not text:
        return text

    result = text

    # Phone numbers → [PHONE]
    result = _PHONE_RE.sub("[PHONE]", result)

    # Emails → [EMAIL]
    result = _EMAIL_RE.sub("[EMAIL]", result)

    # National ID → [ID]
    result = _NATIONAL_ID_RE.sub("[ID]", result)

    # Name patterns → [NAME]
    for pattern in _NAME_PATTERNS:
        result = re.sub(
            pattern, lambda m: m.group(0).replace(m.group(1), "[NAME]"), result, flags=re.IGNORECASE
        )

    # Address fragments → [ADDRESS]
    for pattern in _ADDRESS_PATTERNS:
        result = re.sub(pattern, "[ADDRESS]", result, flags=re.IGNORECASE)

    return result
