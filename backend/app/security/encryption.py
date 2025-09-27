"""Deterministic encryption utilities for PII fields."""

from __future__ import annotations

import base64
import os
from typing import Callable, Optional

from app.core.config import get_settings
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.types import String, TypeDecorator

_KEY_ENV_VAR = "APP_ENCRYPTION_KEY"
_PREFIX = "enc:"
_NONCE_LEN = 12
_SALT = b"eipr-pii-hkdf"


def _load_key() -> bytes:
    raw = os.getenv(_KEY_ENV_VAR)
    if not raw:
        settings = get_settings()
        raw = settings.app_encryption_key
    if not raw:
        raise RuntimeError(f"{_KEY_ENV_VAR} must be configured")
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    decoded: bytes | None = None
    decoders: tuple[Callable[[bytes], bytes], ...] = (
        base64.urlsafe_b64decode,
        base64.b64decode,
    )
    for decoder in decoders:
        try:
            decoded = decoder(raw_bytes)
        except Exception:  # pragma: no cover - try next decoding strategy
            continue
        if decoded:
            break
    if not decoded:
        raise RuntimeError("APP_ENCRYPTION_KEY is not valid base64 data")
    if len(decoded) < 32:
        raise RuntimeError("APP_ENCRYPTION_KEY must decode to at least 32 bytes")
    return decoded


class _DeterministicCipher:
    """Deterministic AES-GCM cipher derived from a master key."""

    def __init__(self, master_key: bytes) -> None:
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=_SALT, info=b"pii")
        expanded = hkdf.derive(master_key)
        self._enc_key = expanded[:32]
        self._nonce_key = expanded[32:]
        self._aesgcm = AESGCM(self._enc_key)

    def _nonce_for(self, plain: bytes) -> bytes:
        mac = hmac.HMAC(self._nonce_key, hashes.SHA256())
        mac.update(plain)
        digest = mac.finalize()
        return digest[:_NONCE_LEN]

    def encrypt(self, plain: str) -> str:
        data = plain.encode("utf-8")
        nonce = self._nonce_for(data)
        cipher = self._aesgcm.encrypt(nonce, data, None)
        token = base64.urlsafe_b64encode(nonce + cipher).decode("utf-8")
        return _PREFIX + token

    def decrypt(self, token: str) -> Optional[str]:
        if not token.startswith(_PREFIX):
            return token
        payload = token[len(_PREFIX) :]
        try:
            blob = base64.urlsafe_b64decode(payload.encode("utf-8"))
        except Exception:  # pragma: no cover - invalid ciphertext
            return None
        if len(blob) <= _NONCE_LEN:
            return None
        nonce, cipher = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        try:
            data = self._aesgcm.decrypt(nonce, cipher, None)
        except Exception:  # pragma: no cover - corrupt token
            return None
        return data.decode("utf-8")


_cipher = _DeterministicCipher(_load_key())


def encrypt_str(value: Optional[str]) -> Optional[str]:
    """Encrypt a string if present."""
    if value is None or value == "":
        return value
    if isinstance(value, str) and value.startswith(_PREFIX):
        return value
    return _cipher.encrypt(value)


def decrypt_str(value: Optional[str]) -> Optional[str]:
    """Decrypt a string when prefixed with the sentinel."""
    if value is None or value == "":
        return value
    if isinstance(value, str):
        return _cipher.decrypt(value)
    return value


class EncryptedStr(TypeDecorator):
    """SQLAlchemy type decorator that transparently encrypts/decrypts strings."""

    impl = String
    cache_ok = True

    def __init__(self, length: int | None = None) -> None:
        super().__init__()
        self.length = length

    def load_dialect_impl(self, dialect):
        if self.length is not None:
            return dialect.type_descriptor(String(self.length))
        return dialect.type_descriptor(String())

    def process_bind_param(self, value: Optional[str], dialect):
        return encrypt_str(value)

    def process_result_value(self, value: Optional[str], dialect):
        return decrypt_str(value)
