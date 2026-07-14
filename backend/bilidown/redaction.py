from __future__ import annotations

import re


_COOKIE_RE = re.compile(r"(?i)(SESSDATA|bili_jct|DedeUserID|buvid3)=([^;\s]+)")
_SIGNED_URL_RE = re.compile(r"https://[^\s]+(?:deadline|upsig|token|sign)=[^\s]+", re.IGNORECASE)


def redact_message(message: str) -> str:
    redacted = _COOKIE_RE.sub(r"\1=<redacted>", message)
    redacted = _SIGNED_URL_RE.sub("<signed-media-url>", redacted)
    return redacted[:4000]
