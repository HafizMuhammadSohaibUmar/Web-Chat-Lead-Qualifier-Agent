"""Security, session token, PII, and rate-limit helpers."""
import re
import base64
import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque

from fastapi import Header, HTTPException, Request
try:
    from jose import JWTError, jwt
except ImportError:  # pragma: no cover - production installs python-jose
    JWTError = ValueError
    jwt = None

from config import get_settings

CC_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
SAFE_CHARS_RE = re.compile(r"[^\w\s.,?!@#+:;/'\"()&-]")

_ip_events: dict[str, Deque[float]] = defaultdict(deque)


def create_session_token(business_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "business_id": business_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.session_expiry_minutes)).timestamp()),
    }
    if jwt:
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64(hmac.new(settings.jwt_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_session_token(token: str) -> dict:
    try:
        if jwt:
            return jwt.decode(token, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(get_settings().jwt_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Bad signature")
        payload = json.loads(base64.urlsafe_b64decode(_pad(body)))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError("Expired")
        return payload
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _pad(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")


def sanitize_user_input(text: str, *, max_len: int = 900) -> str:
    bounded = (text or "")[:max_len]
    return SAFE_CHARS_RE.sub("", bounded).strip()


def assert_no_blocked_pii(text: str) -> None:
    if CC_RE.search(text or "") or SSN_RE.search(text or ""):
        raise HTTPException(status_code=400, detail="Please do not enter credit-card or SSN information.")


def detect_prompt_injection(text: str) -> bool:
    lowered = (text or "").lower()
    patterns = (
        "ignore previous instructions",
        "reveal your system prompt",
        "print your instructions",
        "developer message",
        "system prompt",
        "jailbreak",
    )
    return any(pattern in lowered for pattern in patterns)


async def require_admin_key(x_leadpilot_key: str = Header(default="")) -> None:
    if x_leadpilot_key != get_settings().admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


def enforce_ip_rate_limit(request: Request) -> None:
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    events = _ip_events[ip]
    while events and now - events[0] > 60:
        events.popleft()
    if len(events) >= settings.max_messages_per_ip_minute:
        raise HTTPException(status_code=429, detail="Too many messages from this IP.")
    events.append(now)
