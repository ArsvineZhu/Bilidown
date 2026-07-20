from collections.abc import Mapping

import httpx
import pytest

from bilidown.cookies import CookieStore, InvalidCookieFile
from bilidown.qr_login import (
    BilibiliQrLogin,
    QrHttpResponse,
    QrLoginError,
)


def qr_response(
    data: dict[str, object],
    *,
    cookies: tuple[tuple[str, str], ...] = (),
) -> QrHttpResponse:
    return QrHttpResponse(
        payload={"code": 0, "data": data},
        cookies=cookies,
    )


def test_start_returns_local_svg_data_uri() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {
                "qrcode_key": "a" * 32,
                "url": "https://account.bilibili.com/h5/account-h5/auth/scan-web?qrcode_key=abc",
            }
        )
    )

    result = login.start()

    assert result.qr_key == "a" * 32
    assert result.image_data_uri.startswith("data:image/svg+xml;base64,")


@pytest.mark.parametrize(
    ("code", "state"),
    [(86101, "pending"), (86090, "scanned"), (86038, "expired")],
)
def test_poll_maps_incomplete_login_states(code: int, state: str) -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response({"code": code})
    )

    result = login.poll("a" * 32, CookieStore())

    assert result.state == state
    assert result.session_id is None
    assert result.cookie_count == 0


def test_poll_accepts_biligame_cross_domain_fallback() -> None:
    def request_json(
        url: str,
        params: Mapping[str, str] | None,
    ) -> QrHttpResponse:
        assert url.endswith("/poll")
        assert params == {"qrcode_key": "a" * 32}
        return qr_response(
            {
                "code": 0,
                "url": (
                    "https://passport.biligame.com/crossDomain?SESSDATA=secret&"
                    "bili_jct=csrf&DedeUserID=42&untrusted=value"
                ),
            }
        )

    cookies = CookieStore()
    result = BilibiliQrLogin(request_json).poll("a" * 32, cookies)

    assert result.state == "confirmed"
    assert result.session_id is not None
    assert result.cookie_count == 3
    content = cookies.get(result.session_id).content
    assert "SESSDATA\tsecret" in content
    assert "bili_jct\tcsrf" in content
    assert "DedeUserID\t42" in content
    assert "untrusted" not in content


def test_poll_prefers_allowlisted_response_cookies() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {"code": 0},
            cookies=(
                ("SESSDATA", "header-session"),
                ("bili_jct", "header-csrf"),
                ("not_allowed", "discarded"),
            ),
        )
    )
    cookies = CookieStore()

    result = login.poll("a" * 32, cookies)

    assert result.session_id is not None
    content = cookies.get(result.session_id).content
    assert "SESSDATA\theader-session" in content
    assert "bili_jct\theader-csrf" in content
    assert "not_allowed" not in content


def test_http_transport_collects_set_cookie_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(
        url: str,
        *,
        params: Mapping[str, str] | None,
        headers: Mapping[str, str],
        timeout: int,
    ) -> httpx.Response:
        assert url.endswith("/poll")
        assert params == {"qrcode_key": "a" * 32}
        assert headers["User-Agent"].startswith("Bilidown/")
        assert timeout == 10
        return httpx.Response(
            200,
            json={"code": 0, "data": {"code": 0}},
            headers=[
                (
                    "set-cookie",
                    "SESSDATA=header-session; Domain=.bilibili.com; Path=/; Secure; HttpOnly",
                ),
                (
                    "set-cookie",
                    "bili_jct=header-csrf; Domain=.bilibili.com; Path=/; Secure",
                ),
                (
                    "set-cookie",
                    "not_allowed=discarded; Domain=.bilibili.com; Path=/; Secure",
                ),
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("bilidown.qr_login.httpx.get", fake_get)
    cookies = CookieStore()

    result = BilibiliQrLogin().poll("a" * 32, cookies)

    assert result.session_id is not None
    content = cookies.get(result.session_id).content
    assert "SESSDATA\theader-session" in content
    assert "bili_jct\theader-csrf" in content
    assert "not_allowed" not in content


def test_poll_merges_partial_headers_over_url_fallback() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {
                "code": 0,
                "url": (
                    "https://passport.biligame.com/crossDomain?"
                    "SESSDATA=url-session&bili_jct=url-csrf"
                ),
            },
            cookies=(("bili_jct", "header-csrf"),),
        )
    )
    cookies = CookieStore()

    result = login.poll("a" * 32, cookies)

    assert result.session_id is not None
    content = cookies.get(result.session_id).content
    assert "SESSDATA\turl-session" in content
    assert "bili_jct\theader-csrf" in content
    assert "url-csrf" not in content


def test_poll_accepts_strict_legacy_bilibili_fallback() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {
                "code": 0,
                "url": (
                    "https://passport.bilibili.com/account?"
                    "SESSDATA=legacy-session"
                ),
            }
        )
    )

    result = login.poll("a" * 32, CookieStore())

    assert result.state == "confirmed"
    assert result.cookie_count == 1


def test_poll_rejects_confirmation_without_bilibili_session() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {
                "code": 0,
                "url": "https://passport.bilibili.com/account?bili_jct=csrf",
            }
        )
    )

    with pytest.raises(InvalidCookieFile, match="SESSDATA"):
        login.poll("a" * 32, CookieStore())


@pytest.mark.parametrize(
    "redirect_url",
    [
        "http://passport.biligame.com/crossDomain?SESSDATA=secret",
        "https://passport.biligame.com.evil.example/crossDomain?SESSDATA=secret",
        "https://passport.biligame.com/not-cross-domain?SESSDATA=secret",
        "https://user@passport.biligame.com/crossDomain?SESSDATA=secret",
        "https://passport.bilibili.com/login?SESSDATA=secret",
    ],
)
def test_poll_rejects_hostile_redirects_without_leaking_values(
    redirect_url: str,
) -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response(
            {"code": 0, "url": redirect_url}
        )
    )

    with pytest.raises(InvalidCookieFile) as error:
        login.poll("a" * 32, CookieStore())

    assert str(error.value) == "Bilibili returned an invalid login redirect"
    assert "secret" not in str(error.value)


def test_poll_rejects_unknown_bilibili_status() -> None:
    login = BilibiliQrLogin(
        lambda _url, _params: qr_response({"code": 12345})
    )

    with pytest.raises(QrLoginError, match="status"):
        login.poll("a" * 32, CookieStore())
