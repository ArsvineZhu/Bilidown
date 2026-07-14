from pathlib import Path

import pytest

from bilidown.cookies import CookieStore, InvalidCookieFile, filter_netscape_cookies
from bilidown.models import CookieSessionAuth


COOKIE_FILE = """# Netscape HTTP Cookie File
.bilibili.com\tTRUE\t/\tTRUE\t0\tSESSDATA\tsecret
.example.com\tTRUE\t/\tTRUE\t0\tOTHER\tvalue
#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t0\tbili_jct\tcsrf
"""


def test_filters_non_bilibili_cookies() -> None:
    filtered, count = filter_netscape_cookies(COOKIE_FILE)
    assert count == 2
    assert "SESSDATA" in filtered
    assert "bili_jct" in filtered
    assert "example.com" not in filtered


def test_rejects_non_netscape_file() -> None:
    with pytest.raises(InvalidCookieFile, match="Netscape"):
        filter_netscape_cookies("SESSDATA=secret")


def test_cookie_session_uses_short_lived_file() -> None:
    store = CookieStore()
    session = store.create(COOKIE_FILE)
    auth = CookieSessionAuth(session_id=session.id)
    with store.yt_dlp_options(auth) as options:
        path = Path(str(options["cookiefile"]))
        assert path.exists()
        assert "example.com" not in path.read_text(encoding="utf-8")
    assert not path.exists()

