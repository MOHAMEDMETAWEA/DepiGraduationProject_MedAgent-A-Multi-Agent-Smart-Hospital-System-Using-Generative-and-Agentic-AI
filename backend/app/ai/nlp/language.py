"""
NLP — Language Detection & Arabic Normalization

بيكتشف لغة النص (عربي/إنجليزي/كود-سويتشينج) ويعمل تطبيع للنصوص العربية.
§8.3 Stage 1 من الخطة.
"""

import re

# ── Arabic Unicode blocks ──
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_ENGLISH_PATTERN = re.compile(r"[a-zA-Z]")


def detect_language(text: str) -> str:
    """
    بيكتشف لغة النص.

    Returns:
        'ar' — النص كله عربي
        'en' — النص كله إنجليزي
        'mixed' — كود-سويتشينج (عربي + إنجليزي في نفس الرسالة)
    """
    has_arabic = bool(_ARABIC_PATTERN.search(text))
    has_english = bool(_ENGLISH_PATTERN.search(text))

    if has_arabic and has_english:
        return "mixed"
    if has_arabic:
        return "ar"
    return "en"


def has_arabic(text: str) -> bool:
    """هل النص يحتوي على حروف عربية؟"""
    return bool(_ARABIC_PATTERN.search(text))


# ── Arabic normalization mappings ──

# تطبيع أشكال الألف
_ALEF_NORMALIZATION = {
    "\u0622": "\u0627",  # آ → ا (alef with madda)
    "\u0623": "\u0627",  # أ → ا (alef with hamza above)
    "\u0625": "\u0627",  # إ → ا (alef with hamza below)
    "\u0626": "\u0627",  # ئ → ا
    "\u0671": "\u0627",  # ٱ → ا
}

# تطبيع التاء المربوطة → هاء
_TAA_MARBUTA = "\u0629"  # ة
_HEH = "\u0647"  # ه

# تطبيع الحركات (diacritics) — بنشيلهم كلهم
_DIACRITICS_PATTERN = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

# تطبيع علامات الترقيم
_PUNCTUATION_NORMALIZATION = {
    "\u060c": ",",  # ، → ,
    "\u061b": ";",  # ؛ → ;
    "\u061f": "?",  # ؟ → ?
    "\u066a": "%",  # ٪ → %
    "\u066b": ".",  # ٫ → .
    "\u066c": ",",  # ٬ → ,
}


def normalize_arabic(text: str) -> str:
    """
    يطبع النص العربي — بيوحد الأشكال المختلفة لنفس الحروف.

    التحويلات:
    1. كل أشكال الألف (أ إ آ ئ ٱ) → ا
    2. التاء المربوطة (ة) → هاء (ه)
    3. حذف الحركات (الفتحة، الضمة، الكسرة، الشدة، السكون، ...)
    4. تطبيع علامات الترقيم العربية → لاتينية
    5. توحيد المسافات (مسافات متعددة → مسافة واحدة)
    6. Trim المسافات الزائدة

    Args:
        text: النص العربي المطلوب تطبيعه

    Returns:
        النص بعد التطبيع
    """
    # 1. تطبيع الألف
    for k, v in _ALEF_NORMALIZATION.items():
        text = text.replace(k, v)

    # 2. تطبيع التاء المربوطة
    text = text.replace(_TAA_MARBUTA, _HEH)

    # 3. حذف الحركات
    text = _DIACRITICS_PATTERN.sub("", text)

    # 4. تطبيع علامات الترقيم
    for k, v in _PUNCTUATION_NORMALIZATION.items():
        text = text.replace(k, v)

    # 5. توحيد المسافات
    text = re.sub(r"\s+", " ", text)

    # 6. Trim
    text = text.strip()

    return text


def preprocess_message(text: str) -> dict:
    """
    معالجة أولية لرسالة المستخدم — كشف اللغة + تطبيع.

    Returns:
        dict: {original, language, normalized, has_arabic}
    """
    language = detect_language(text)
    normalized = text

    if language in ("ar", "mixed"):
        normalized = normalize_arabic(text)

    return {
        "original": text,
        "language": language,
        "normalized": normalized,
        "has_arabic": has_arabic(text),
    }
