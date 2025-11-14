"""
Utilities for token generation and HMAC signing used in offer links.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Final


def now_epoch() -> int:
    """Current UNIX epoch seconds (UTC)."""
    return int(time.time())


def _b64url_no_pad(data: bytes) -> str:
    """URL-safe base64 without padding, as short opaque tokens/signatures."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def generate_token(nbytes: int = 16) -> str:
    """
    Generate an opaque, URL-safe token.
    Default 16 random bytes → 22-char base64url string (no padding).
    """
    if nbytes <= 0:
        raise ValueError("nbytes must be > 0")
    return _b64url_no_pad(secrets.token_bytes(nbytes))


def sign_token(token: str, offer_id: str, expires_at: int, secret: str | None = None) -> str:
    """
    HMAC-SHA256 over the canonical message: token|offer_id|expires_at.

    Returns a URL-safe base64 (no padding) signature string.

    Args:
        token: Opaque short token placed in the link.
        offer_id: The Offer primary key (e.g., 'OFR-...').
        expires_at: UNIX epoch seconds when the link should expire.
        secret: HMAC secret. If None, read from env TOKEN_SECRET.

    Raises:
        ValueError: if inputs are missing or secret is empty.
    """
    if not token or not offer_id:
        raise ValueError("token and offer_id are required")
    if not isinstance(expires_at, int):
        raise ValueError("expires_at must be an int epoch seconds")

    key: Final[str] = secret or os.getenv("TOKEN_SECRET", "")
    if not key:
        raise ValueError("TOKEN_SECRET is not set")

    msg = f"{token}|{offer_id}|{expires_at}".encode("utf-8")
    digest = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
    return _b64url_no_pad(digest)
