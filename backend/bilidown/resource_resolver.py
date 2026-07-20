from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlsplit

from yt_dlp.cookies import CookieLoadError
from yt_dlp.utils import DownloadError

from .cookies import CookieStore, InvalidCookieFile
from .errors import EngineError, map_engine_error
from .input_parser import NormalizedCredential
from .media_metadata import resolved_video_from_info, safe_cover_preview_url
from .models import AuthConfig, ResolvedResource, ResourceItem, ResourceKind
from .typeguards import as_bool, as_float, as_int, as_mapping, as_mappings, as_optional_str
from .yt_adapter import YtDlpAdapter
from .yt_logging import EngineLogger


BaseOptionsFactory = Callable[[EngineLogger], dict[str, object]]
_BVID_RE = re.compile(r"BV[0-9A-Za-z]{10}", re.IGNORECASE)
_PREVIEW_LIMIT = 100


class ResourceResolver:
    def __init__(
        self,
        cookie_store: CookieStore,
        adapter: YtDlpAdapter,
        base_options: BaseOptionsFactory,
    ) -> None:
        self._cookie_store = cookie_store
        self._adapter = adapter
        self._base_options = base_options

    def resolve(self, canonical_url: str, auth: AuthConfig) -> ResolvedResource:
        logger = EngineLogger()
        try:
            with self._cookie_store.yt_dlp_options(auth) as cookie_options:
                options: dict[str, object] = {
                    **self._base_options(logger),
                    **cookie_options,
                    "skip_download": True,
                    "extract_flat": "in_playlist",
                    "playlistend": _PREVIEW_LIMIT + 1,
                    "lazy_playlist": False,
                    "noplaylist": False,
                }
                raw_info = self._adapter.extract(canonical_url, options)
        except InvalidCookieFile:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请使用应用内一键登录或 cookies.txt",
            ) from exc
        except (DownloadError, OSError) as exc:
            raise map_engine_error(logger.last_error or str(exc)) from exc
        info = as_mapping(raw_info)
        if info is None:
            raise EngineError("invalid_metadata", "Bilibili 返回了无法识别的资源信息")
        return self._to_resource(canonical_url, info)

    @staticmethod
    def _to_resource(canonical_url: str, info: dict[str, object]) -> ResolvedResource:
        kind = _resource_kind(canonical_url, info)
        raw_entries = as_mappings(info.get("entries"))
        entries = raw_entries or [info]
        truncated = len(entries) > _PREVIEW_LIMIT
        preview_entries = entries[:_PREVIEW_LIMIT]
        items = [
            _resource_item(entry, index, canonical_url, kind)
            for index, entry in enumerate(preview_entries, start=1)
        ]
        title = (
            as_optional_str(info.get("playlist_title"))
            or as_optional_str(info.get("series"))
            or as_optional_str(info.get("title"))
            or items[0].title
        )
        total_items = as_int(info.get("playlist_count")) or len(entries)
        total_items = max(total_items, len(items))
        warnings: list[str] = []
        experimental = kind in {ResourceKind.CATEGORY, ResourceKind.SEARCH}
        if truncated or total_items > _PREVIEW_LIMIT:
            warnings.append("preview_limit")
            truncated = True
        if kind == ResourceKind.INTERACTIVE:
            warnings.append("interactive_paths")
        if kind in {
            ResourceKind.FAVORITES,
            ResourceKind.WATCH_LATER,
            ResourceKind.COURSE,
        }:
            warnings.append("login_may_be_required")
        if kind == ResourceKind.LIVE:
            warnings.append("live_requires_recorder")
        video = None
        if kind == ResourceKind.VIDEO and not raw_entries:
            match = _BVID_RE.search(
                as_optional_str(info.get("id"))
                or as_optional_str(info.get("webpage_url"))
                or canonical_url
            )
            fallback = f"BV{match.group(0)[2:]}" if match else "BV0000000000"
            normalized = NormalizedCredential(canonical_url, fallback, 1)
            video = resolved_video_from_info(info, normalized)
        return ResolvedResource(
            canonical_url=canonical_url,
            kind=kind,
            title=title,
            uploader=as_optional_str(info.get("uploader"))
            or as_optional_str(info.get("channel")),
            thumbnail=safe_cover_preview_url(info.get("thumbnail")),
            items=items,
            total_items=total_items,
            truncated=truncated,
            experimental=experimental,
            warnings=warnings,
            video=video,
        )


def _resource_item(
    entry: dict[str, object],
    fallback_index: int,
    source_url: str,
    kind: ResourceKind,
) -> ResourceItem:
    index = as_int(entry.get("playlist_index")) or fallback_index
    identifier = (
        as_optional_str(entry.get("id"))
        or as_optional_str(entry.get("display_id"))
        or f"item-{index}"
    )
    url = (
        as_optional_str(entry.get("webpage_url"))
        or as_optional_str(entry.get("original_url"))
        or as_optional_str(entry.get("url"))
        or source_url
    )
    if not url.startswith(("http://", "https://")):
        match = _BVID_RE.search(identifier)
        url = (
            f"https://www.bilibili.com/video/BV{match.group(0)[2:]}"
            if match
            else source_url
        )
    title = (
        as_optional_str(entry.get("title"))
        or as_optional_str(entry.get("fulltitle"))
        or identifier
    )
    live_status = as_optional_str(entry.get("live_status"))
    is_branch = kind == ResourceKind.INTERACTIVE or (
        "_" in identifier and identifier.startswith("BV")
    )
    return ResourceItem(
        index=index,
        id=identifier,
        url=url,
        title=title,
        uploader=as_optional_str(entry.get("uploader"))
        or as_optional_str(entry.get("channel")),
        duration=as_float(entry.get("duration")),
        thumbnail=safe_cover_preview_url(entry.get("thumbnail")),
        live=kind == ResourceKind.LIVE
        or live_status == "is_live"
        or as_bool(entry.get("is_live")),
        branch=is_branch,
    )


def _resource_kind(url: str, info: dict[str, object]) -> ResourceKind:
    extractor = (
        as_optional_str(info.get("extractor_key"))
        or as_optional_str(info.get("extractor"))
        or ""
    ).lower()
    path = urlsplit(url).path.lower()
    if "bililive" in extractor or "live.bilibili.com" in url:
        return ResourceKind.LIVE
    if "intl" in extractor or "bilibili.tv" in url or "biliintl.com" in url:
        return ResourceKind.INTERNATIONAL
    if "bangumi" in extractor or "/bangumi/" in path:
        return ResourceKind.BANGUMI
    if "cheese" in extractor or "/cheese/" in path:
        return ResourceKind.COURSE
    if "favorites" in extractor or "favlist" in url or "/medialist/detail/" in path:
        return ResourceKind.FAVORITES
    if "collection" in extractor:
        return ResourceKind.COLLECTION
    if "serieslist" in extractor:
        return ResourceKind.SERIES
    if "watchlater" in extractor or "/watchlater" in path:
        return ResourceKind.WATCH_LATER
    if "space" in extractor or "space.bilibili.com" in url:
        return ResourceKind.SPACE
    if "audio" in extractor or "/audio/" in path:
        return ResourceKind.AUDIO
    if "dynamic" in extractor or "/opus/" in path or "t.bilibili.com" in url:
        return ResourceKind.DYNAMIC
    if "category" in extractor:
        return ResourceKind.CATEGORY
    if "search" in extractor:
        return ResourceKind.SEARCH
    if "playlist" in extractor or "/list/" in path or "/medialist/play/" in path:
        return ResourceKind.PLAYLIST
    entries = as_mappings(info.get("entries"))
    if any("_" in (as_optional_str(entry.get("id")) or "") for entry in entries):
        return ResourceKind.INTERACTIVE
    if "bilibili" in extractor or "/video/" in path or "/festival/" in path:
        return ResourceKind.VIDEO
    return ResourceKind.UNKNOWN
