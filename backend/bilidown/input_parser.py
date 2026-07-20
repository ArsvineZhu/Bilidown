from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

import httpx


_BVID_RE = re.compile(r"^BV[0-9A-Za-z]{10}$", re.IGNORECASE)
_AVID_RE = re.compile(r"^av([0-9]+)$", re.IGNORECASE)
_VIDEO_PATH_RE = re.compile(r"^/video/(BV[0-9A-Za-z]{10}|av[0-9]+)(?:/)?$", re.IGNORECASE)
_BILIBILI_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com"}
_BILIBILI_RESOURCE_HOSTS = _BILIBILI_HOSTS | {
    "space.bilibili.com",
    "live.bilibili.com",
    "player.bilibili.com",
    "t.bilibili.com",
    "bilibili.tv",
    "www.bilibili.tv",
    "biliintl.com",
    "www.biliintl.com",
}
_SHORT_HOSTS = {"b23.tv", "www.b23.tv"}


class InvalidCredential(ValueError):
    """Raised when a user supplied value is not a supported video credential."""


@dataclass(frozen=True)
class NormalizedCredential:
    canonical_url: str
    video_id: str
    selected_page: int


def _normalize_video_id(value: str) -> str:
    if _BVID_RE.fullmatch(value):
        return f"BV{value[2:]}"
    av_match = _AVID_RE.fullmatch(value)
    if av_match:
        return f"av{av_match.group(1)}"
    raise InvalidCredential("只支持 BV 号、带 av 前缀的 AV 号或视频链接")


def _normalize_bilibili_url(url: str) -> NormalizedCredential:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise InvalidCredential("视频链接必须使用 HTTPS")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in _BILIBILI_HOSTS:
        raise InvalidCredential("链接必须指向 bilibili.com 视频页面")
    path_match = _VIDEO_PATH_RE.fullmatch(parsed.path)
    if not path_match:
        raise InvalidCredential("首版只支持 bilibili.com/video 下的普通投稿")
    video_id = _normalize_video_id(path_match.group(1))
    page_values = parse_qs(parsed.query).get("p", ["1"])
    try:
        selected_page = int(page_values[-1])
    except ValueError as exc:
        raise InvalidCredential("分 P 参数必须是正整数") from exc
    if selected_page < 1:
        raise InvalidCredential("分 P 参数必须从 1 开始")
    query = f"p={selected_page}" if selected_page != 1 else ""
    canonical = urlunsplit(("https", "www.bilibili.com", f"/video/{video_id}", query, ""))
    return NormalizedCredential(canonical, video_id, selected_page)


async def _resolve_short_url(url: str, client: httpx.AsyncClient) -> str:
    current = url
    for _ in range(5):
        parsed = urlsplit(current)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme.lower() != "https" or host not in _SHORT_HOSTS | _BILIBILI_RESOURCE_HOSTS:
            raise InvalidCredential("短链跳转到了不受信任的地址")
        if host in _BILIBILI_RESOURCE_HOSTS:
            return current
        try:
            request = client.build_request(
                "GET",
                current,
                headers={
                    "User-Agent": "Bilidown/0.1",
                    "Range": "bytes=0-0",
                },
            )
            response = await client.send(request, follow_redirects=False, stream=True)
        except httpx.HTTPError as exc:
            raise InvalidCredential("无法解析 b23.tv 短链") from exc
        try:
            if response.status_code not in {301, 302, 303, 307, 308}:
                raise InvalidCredential("b23.tv 未返回有效的视频跳转")
            location = cast(str | None, response.headers.get("location"))
            if not location or len(location) > 4096:
                raise InvalidCredential("短链跳转地址无效")
            current = urljoin(current, location)
        finally:
            await response.aclose()
    raise InvalidCredential("短链跳转次数过多")


async def normalize_credential(
    value: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> NormalizedCredential:
    value = value.strip()
    if _BVID_RE.fullmatch(value) or _AVID_RE.fullmatch(value):
        video_id = _normalize_video_id(value)
        return NormalizedCredential(
            f"https://www.bilibili.com/video/{video_id}",
            video_id,
            1,
        )

    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in _SHORT_HOSTS:
        if parsed.scheme.lower() != "https":
            raise InvalidCredential("短链必须使用 HTTPS")
        if client is not None:
            resolved = await _resolve_short_url(value, client)
        else:
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as owned_client:
                resolved = await _resolve_short_url(value, owned_client)
        return _normalize_bilibili_url(resolved)

    if parsed.scheme or parsed.netloc:
        return _normalize_bilibili_url(value)
    raise InvalidCredential("无法识别该视频凭据")


async def normalize_resource_url(
    value: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> str:
    value = value.strip()
    if _BVID_RE.fullmatch(value) or _AVID_RE.fullmatch(value):
        return (await normalize_credential(value, client=client)).canonical_url
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in _SHORT_HOSTS:
        if parsed.scheme.lower() != "https":
            raise InvalidCredential("短链必须使用 HTTPS")
        if client is not None:
            value = await _resolve_short_url(value, client)
        else:
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as owned_client:
                value = await _resolve_short_url(value, owned_client)
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https":
        raise InvalidCredential("Bilibili 链接必须使用 HTTPS")
    try:
        has_custom_port = parsed.port is not None
    except ValueError as exc:
        raise InvalidCredential("Bilibili 链接端口无效") from exc
    if parsed.username or parsed.password or has_custom_port:
        raise InvalidCredential("Bilibili 链接不能包含凭据或自定义端口")
    if host not in _BILIBILI_RESOURCE_HOSTS:
        raise InvalidCredential("链接必须指向受支持的 Bilibili 页面")
    path = parsed.path or "/"
    return urlunsplit(("https", host, path, parsed.query, ""))
