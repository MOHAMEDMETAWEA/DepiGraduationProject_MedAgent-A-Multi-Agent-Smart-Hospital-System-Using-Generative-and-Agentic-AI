"""
PHI Field Encryption — تشفير البيانات الطبية الحساسة (AES-128-CBC + HMAC-SHA256)

بنستخدم Fernet من مكتبة cryptography عشان نشفر الحقول دي قبل ما تتخزن في الداتابيز:
- messages.content → messages.encrypted_content
- vision_analyses.analysis → vision_analyses.encrypted_analysis
- patient_profiles (allergies, conditions, medications as encrypted blob)
- handoff_summaries.summary_markdown

المفتاح بيجي من DATA_ENCRYPTION_KEY في متغيرات البيئة.
لو PHI_ENCRYPTION_ENABLED=false (للتطوير المحلي)، بنستخدم content العادي.

§9.6 من الخطة.
"""

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet | None:
    """
    يرجع instance من Fernet باستخدام المفتاح من الإعدادات.

    لو المفتاح مش موجود أو التشفير متعطل: يرجع None.
    """
    if not settings.PHI_ENCRYPTION_ENABLED:
        return None

    key = settings.DATA_ENCRYPTION_KEY
    if not key:
        # في production، غياب المفتاح = خطأ (بنوقفه في config.py model_post_init)
        if settings.is_production:
            raise RuntimeError("DATA_ENCRYPTION_KEY is required in production")
        return None

    # بنستخدم مفتاح واحد (single key)
    # MultiFernet جاهز لو عايزين dual-key rotation
    return Fernet(key.encode() if isinstance(key, str) else key)


# Singleton — بننشئه مرة واحدة
_fernet = _get_fernet()


def is_encryption_enabled() -> bool:
    """هل التشفير شغال؟"""
    return _fernet is not None


def encrypt_phi(plaintext: str) -> bytes:
    """
    يشفر نص عادي → bytes مشفر (Fernet token).

    لو التشفير مش شغال: يرجع النص كـ bytes عادي.

    Args:
        plaintext: النص العادي (بيانات المريض)

    Returns:
        bytes: الـ ciphertext (أو plaintext لو التشفير متعطل)
    """
    if _fernet is None:
        return plaintext.encode("utf-8")
    return _fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_phi(ciphertext: bytes) -> str:
    """
    يفك تشفير bytes → نص مقروء.

    لو التشفير مش شغال: يرجع الـ bytes كـ string عادي.

    Args:
        ciphertext: الـ bytes المشفر (أو plaintext لو التشفير متعطل)

    Returns:
        str: النص الأصلي
    """
    if _fernet is None:
        if isinstance(ciphertext, bytes):
            return ciphertext.decode("utf-8")
        return str(ciphertext)
    return _fernet.decrypt(ciphertext).decode("utf-8")


def rotate_key(old_key: str, new_key: str, data: bytes) -> bytes:
    """
    تدوير المفتاح: يفك تشفير البيانات بالمفتاح القديم ويشفرها بالجديد.

    بنستخدمها في عملية key rotation المخططة.

    Args:
        old_key: المفتاح القديم (str)
        new_key: المفتاح الجديد (str)
        data: البيانات المشفرة بالمفتاح القديم

    Returns:
        bytes: البيانات مشفرة بالمفتاح الجديد
    """
    old_fernet = Fernet(old_key.encode() if isinstance(old_key, str) else old_key)
    new_fernet = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
    return new_fernet.encrypt(old_fernet.decrypt(data))


def generate_key() -> str:
    """يولّد مفتاح Fernet جديد (للاستخدام لمرة واحدة في الـ setup)."""
    return Fernet.generate_key().decode()
