import base64
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

PROVIDER_PRESETS = {
    "openai": ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
    "groq": ("Groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat"),
    "gemini": ("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-flash"),
    "openrouter": ("OpenRouter", "https://openrouter.ai/api/v1", "auto"),
}


def _derive_ai_key() -> bytes:
    secret = (settings.SECRET_KEY or "dev-insecure-key").encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"jobbloot-ai-config-v1",
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret))


def encrypt_api_key(plain: str) -> str:
    f = Fernet(_derive_ai_key())
    return f.encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = Fernet(_derive_ai_key())
    return f.decrypt(encrypted.encode()).decode()


class AIConfig(models.Model):
    provider = models.CharField(max_length=50, default="openai")
    api_base_url = models.CharField(max_length=255, default="https://api.openai.com/v1")
    encrypted_api_key = models.TextField(default="")
    model_name = models.CharField(max_length=100, default="gpt-4o-mini")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Config"
        verbose_name_plural = "AI Config"

    def __str__(self):
        return f"AIConfig({self.provider}/{self.model_name})"

    def set_api_key(self, plain: str):
        self.encrypted_api_key = encrypt_api_key(plain)

    def get_api_key(self) -> str:
        if not self.encrypted_api_key:
            return ""
        try:
            return decrypt_api_key(self.encrypted_api_key)
        except Exception as e:
            logger.error(f"Failed to decrypt AI API key: {e}")
            return ""

    @classmethod
    def load(cls) -> "AIConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def has_ai_config(self) -> bool:
        return bool(self.encrypted_api_key and self.api_base_url)
