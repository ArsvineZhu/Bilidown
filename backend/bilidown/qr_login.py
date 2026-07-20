from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, cast
from urllib.parse import parse_qsl, urlsplit

import httpx
import qrcode
from qrcode.image.svg import SvgPathImage

from .cookies import CookieStore, InvalidCookieFile
from .typeguards import as_int, as_mapping, as_optional_str


_GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
_COOKIE_NAMES = frozenset(
    {
        "SESSDATA",
        "bili_jct",
        "DedeUserID",
        "DedeUserID__ckMd5",
        "sid",
        "buvid3",
        "buvid4",
        "b_nut",
        "b_lsid",
        "buvid_fp",
    }
)
_POLL_STATES: dict[int, Literal["pending", "scanned", "expired"]] = {
    86101: "pending",
    86090: "scanned",
    86038: "expired",
}


@dataclass(frozen=True)
class QrHttpResponse:
    payload: dict[str, object]
    cookies: tuple[tuple[str, str], ...] = ()


JsonRequester = Callable[[str, Mapping[str, str] | None], QrHttpResponse]


class QrLoginError(RuntimeError):
    """Raised when the Bilibili QR login protocol returns unusable data."""


@dataclass(frozen=True)
class QrLoginStartData:
    qr_key: str
    image_data_uri: str


@dataclass(frozen=True)
class QrLoginPollData:
    state: Literal["pending", "scanned", "confirmed", "expired"]
    session_id: str | None = None
    cookie_count: int = 0


class BilibiliQrLogin:
    def __init__(self, request_json: JsonRequester | None = None) -> None:
        self._request_json = request_json or _request_json

    def start(self) -> QrLoginStartData:
        response = self._request_json(_GENERATE_URL, None)
        data = _response_data(response.payload)
        qr_key = as_optional_str(data.get("qrcode_key"))
        qr_url = as_optional_str(data.get("url"))
        if qr_key is None or qr_url is None or not 16 <= len(qr_key) <= 128:
            raise QrLoginError("Bilibili returned an invalid QR login code")
        return QrLoginStartData(qr_key=qr_key, image_data_uri=_svg_data_uri(qr_url))

    def poll(self, qr_key: str, cookies: CookieStore) -> QrLoginPollData:
        if not 16 <= len(qr_key) <= 128:
            raise QrLoginError("QR login code is invalid")
        response = self._request_json(_POLL_URL, {"qrcode_key": qr_key})
        data = _response_data(response.payload)
        status = as_int(data.get("code"))
        if status == 0:
            redirect_url = as_optional_str(data.get("url"))
            session = cookies.create(
                _netscape_cookies(response.cookies, redirect_url)
            )
            return QrLoginPollData(
                state="confirmed",
                session_id=session.id,
                cookie_count=session.cookie_count,
            )
        if status in _POLL_STATES:
            return QrLoginPollData(state=_POLL_STATES[status])
        raise QrLoginError("Bilibili QR login status is unavailable")


def _request_json(url: str, params: Mapping[str, str] | None) -> QrHttpResponse:
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"User-Agent": "Bilidown/1.0 (local QR login)"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise QrLoginError("Unable to reach Bilibili QR login") from exc
    try:
        payload = cast(object, response.json())
    except ValueError as exc:
        raise QrLoginError(
            "Bilibili QR login returned an invalid response"
        ) from exc
    data = as_mapping(payload)
    if data is None:
        raise QrLoginError("Bilibili QR login returned an invalid response")
    return QrHttpResponse(
        payload=data,
        cookies=tuple(response.cookies.items()),
    )


def _response_data(payload: dict[str, object]) -> dict[str, object]:
    if as_int(payload.get("code")) != 0:
        raise QrLoginError("Bilibili QR login request was rejected")
    data = as_mapping(payload.get("data"))
    if data is None:
        raise QrLoginError("Bilibili QR login returned an invalid response")
    return data


def _svg_data_uri(value: str) -> str:
    image = qrcode.make(value, image_factory=SvgPathImage, border=2)
    svg = cast(bytes, image.to_string(encoding="utf-8"))
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


def _netscape_cookies(
    response_cookies: tuple[tuple[str, str], ...],
    redirect_url: str | None,
) -> str:
    header_values = _allowlisted_cookie_values(response_cookies)
    if header_values.get("SESSDATA"):
        return _format_netscape_cookies(header_values)
    if redirect_url is None:
        raise InvalidCookieFile("Bilibili login did not return SESSDATA")
    redirect_values = _redirect_cookie_values(redirect_url)
    return _format_netscape_cookies({**redirect_values, **header_values})


def _allowlisted_cookie_values(
    cookie_pairs: tuple[tuple[str, str], ...],
) -> dict[str, str]:
    return {
        name: value
        for name, value in cookie_pairs
        if name in _COOKIE_NAMES
    }


def _redirect_cookie_values(redirect_url: str) -> dict[str, str]:
    try:
        parsed = urlsplit(redirect_url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidCookieFile(
            "Bilibili returned an invalid login redirect"
        ) from exc
    allowed_target = (
        parsed.hostname == "passport.biligame.com"
        and parsed.path == "/crossDomain"
    ) or (
        parsed.hostname == "passport.bilibili.com"
        and parsed.path == "/account"
    )
    if (
        parsed.scheme != "https"
        or not allowed_target
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    ):
        raise InvalidCookieFile("Bilibili returned an invalid login redirect")
    values = dict(parse_qsl(parsed.query, keep_blank_values=False))
    return _allowlisted_cookie_values(tuple(values.items()))


def _format_netscape_cookies(values: Mapping[str, str]) -> str:
    if not values.get("SESSDATA"):
        raise InvalidCookieFile("Bilibili login did not return SESSDATA")
    lines = ["# Netscape HTTP Cookie File"]
    for name in sorted(_COOKIE_NAMES.intersection(values.keys())):
        value = values[name]
        if "\t" in value or "\n" in value or "\r" in value:
            raise InvalidCookieFile("Bilibili login returned an invalid cookie")
        lines.append(f"#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}")
    return "\n".join(lines) + "\n"
