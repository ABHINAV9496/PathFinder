import base64
import hashlib
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def _derive_key() -> bytes:
    secret = (settings.SECRET_KEY or "dev-insecure-key").encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"jobbloot-cred-store-v1",
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret))


def encrypt_password(plain: str) -> str:
    f = Fernet(_derive_key())
    return f.encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    f = Fernet(_derive_key())
    return f.decrypt(encrypted.encode()).decode()


class CredStore(models.Model):
    sender_email = models.EmailField(default="")
    encrypted_password = models.TextField(default="")
    resume_file = models.FileField(upload_to="resumes/", blank=True)
    resume_original_name = models.CharField(max_length=255, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Credential Store"
        verbose_name_plural = "Credential Store"

    def __str__(self):
        return f"CredStore({self.sender_email})"

    def set_password(self, plain: str):
        self.encrypted_password = encrypt_password(plain)

    def get_password(self) -> str:
        if not self.encrypted_password:
            return ""
        try:
            return decrypt_password(self.encrypted_password)
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            return ""

    @classmethod
    def load(cls) -> "CredStore":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def has_credentials(self) -> bool:
        return bool(self.sender_email and self.encrypted_password)

    @property
    def has_resume(self) -> bool:
        return bool(self.resume_file)

    @property
    def resume_size_kb(self) -> int:
        if not self.resume_file:
            return 0
        try:
            return round(self.resume_file.size / 1024)
        except Exception:
            return 0
