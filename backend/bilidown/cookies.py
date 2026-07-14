from __future__ import annotations

import contextlib
import os
import secrets
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .models import AuthConfig, BrowserAuth, CookieSessionAuth


class InvalidCookieFile(ValueError):
    """Raised when a cookie file is malformed or contains no Bilibili cookies."""


@dataclass(frozen=True)
class CookieSession:
    id: str
    content: str
    cookie_count: int


def filter_netscape_cookies(content: str) -> tuple[str, int]:
    if len(content.encode("utf-8")) > 1024 * 1024:
        raise InvalidCookieFile("Cookie 文件不能超过 1 MiB")
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() not in {
        "# Netscape HTTP Cookie File",
        "# HTTP Cookie File",
    }:
        raise InvalidCookieFile("Cookie 文件必须使用 Netscape 格式")

    kept: list[str] = ["# Netscape HTTP Cookie File"]
    count = 0
    for raw_line in lines[1:]:
        line = raw_line.strip()
        if not line:
            continue
        data_line = line
        if line.startswith("#HttpOnly_"):
            data_line = line[len("#HttpOnly_") :]
        elif line.startswith("#"):
            continue
        fields = data_line.split("\t")
        if len(fields) != 7:
            continue
        domain = fields[0].lstrip(".").lower()
        if domain == "bilibili.com" or domain.endswith(".bilibili.com"):
            kept.append(raw_line.strip())
            count += 1
    if count == 0:
        raise InvalidCookieFile("Cookie 文件中没有 Bilibili 登录信息")
    return "\n".join(kept) + "\n", count


class CookieStore:
    def __init__(self) -> None:
        self._sessions: dict[str, CookieSession] = {}
        self._lock = threading.Lock()

    def create(self, content: str) -> CookieSession:
        filtered, count = filter_netscape_cookies(content)
        session = CookieSession(secrets.token_urlsafe(24), filtered, count)
        with self._lock:
            self._sessions[session.id] = session
        return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def get(self, session_id: str) -> CookieSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise InvalidCookieFile("Cookie 会话不存在或已经失效")
        return session

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    @contextlib.contextmanager
    def yt_dlp_options(self, auth: AuthConfig) -> Iterator[dict[str, object]]:
        if isinstance(auth, BrowserAuth):
            yield {"cookiesfrombrowser": (auth.browser, auth.profile, None, None)}
            return
        if not isinstance(auth, CookieSessionAuth):
            yield {}
            return

        session = self.get(auth.session_id)
        handle, raw_path = tempfile.mkstemp(prefix="bilidown-cookie-", suffix=".txt", text=True)
        path = Path(raw_path)
        try:
            os.close(handle)
            path.write_text(session.content, encoding="utf-8", newline="\n")
            with contextlib.suppress(OSError):
                path.chmod(0o600)
            yield {"cookiefile": str(path)}
        finally:
            with contextlib.suppress(OSError):
                path.unlink()

