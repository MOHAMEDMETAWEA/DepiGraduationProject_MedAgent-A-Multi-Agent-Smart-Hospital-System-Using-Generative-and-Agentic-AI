"""
SQLAlchemy TypeDecorators — أنواع مخصصة للتعامل مع الحقول المشفرة.

EncryptedString: بيشفر/يفك تشفير النصوص تلقائياً على مستوى ORM.
EncryptedJSON: بيشفر/يفك تشفير JSONB تلقائياً.

لما PHI_ENCRYPTION_ENABLED=false، بيرجع القيم من غير تشفير.

§9.6 من الخطة.
"""

import json

from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from app.core.encryption import decrypt_phi, encrypt_phi, is_encryption_enabled


class EncryptedString(TypeDecorator):
    """
    نوع SQLAlchemy بيشفّر String تلقائياً.

    في الداتابيز: BYTEA (LargeBinary)
    في التطبيق: str
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> bytes | None:
        """بيشفّر القيمة قبل ما تتخزن في الداتابيز."""
        if value is None:
            return None
        if not is_encryption_enabled():
            return value.encode("utf-8") if isinstance(value, str) else value
        return encrypt_phi(value)

    def process_result_value(self, value: bytes | None, dialect) -> str | None:
        """بيفك تشفير القيمة بعد ما تخرج من الداتابيز."""
        if value is None:
            return None
        if not is_encryption_enabled():
            return value.decode("utf-8") if isinstance(value, bytes) else str(value)
        return decrypt_phi(value)


class EncryptedJSON(TypeDecorator):
    """
    نوع SQLAlchemy بيشفّر JSON تلقائياً.

    في الداتابيز: BYTEA (LargeBinary)
    في التطبيق: dict | list
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: dict | list | None, dialect) -> bytes | None:
        """بيشفّر JSON قبل ما يتخزن."""
        if value is None:
            return None
        text = json.dumps(value, ensure_ascii=False)
        if not is_encryption_enabled():
            return text.encode("utf-8")
        return encrypt_phi(text)

    def process_result_value(self, value: bytes | None, dialect) -> dict | list | None:
        """بيفك تشفير JSON بعد ما يخرج من الداتابيز."""
        if value is None:
            return None
        if not is_encryption_enabled():
            text = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            return json.loads(text)
        return json.loads(decrypt_phi(value))
