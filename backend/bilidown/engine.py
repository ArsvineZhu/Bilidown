from __future__ import annotations

import contextlib
import json
import mimetypes
import re
import shutil
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

import httpx
import yt_dlp
from yt_dlp.cookies import CookieLoadError
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadCancelled, DownloadError

from .cookies import CookieStore, InvalidCookieFile
from .files import ensure_output_directory, move_without_overwrite, sanitize_filename
from .input_parser import NormalizedCredential
from .models import (
    AudioFormat,
    AuthStatus,
    CreateJobRequest,
    GuestAuth,
    MediaKind,
    QualityOption,
    ResolvedVideo,
    VideoMode,
    VideoPage,
)
from .redaction import redact_message
from .runtime import ffmpeg_location


ProgressCallback = Callable[[dict[str, Any]], None]
_BVID_SEARCH_RE = re.compile(r"BV[0-9A-Za-z]{10}", re.IGNORECASE)


class EngineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _EngineLogger:
    def __init__(self) -> None:
        self.last_error: str | None = None

    def debug(self, message: str) -> None:
        return None

    def info(self, message: str) -> None:
        return None

    def warning(self, message: str) -> None:
        return None

    def error(self, message: str) -> None:
        self.last_error = redact_message(message)


def _codec_is_h264(codec: str | None) -> bool:
    value = (codec or "").lower()
    return value.startswith(("avc1", "h264"))


def _codec_is_aac(codec: str | None) -> bool:
    value = (codec or "").lower()
    return value.startswith(("mp4a", "aac"))


def _codec_family(codec: str | None) -> str:
    value = (codec or "").lower()
    if value.startswith(("avc1", "h264")):
        return "H.264"
    if value.startswith(("hvc1", "hev1", "hevc", "h265")):
        return "HEVC"
    if value.startswith(("av01", "av1")):
        return "AV1"
    return "Other"


def _is_sdr(dynamic_range: str | None) -> bool:
    return (dynamic_range or "SDR").upper() in {"SDR", "SDR10"}


def _extract_bvid(info: dict[str, Any], fallback: str) -> str:
    for candidate in (info.get("id"), info.get("display_id"), info.get("webpage_url"), fallback):
        match = _BVID_SEARCH_RE.search(str(candidate or ""))
        if match:
            return f"BV{match.group(0)[2:]}"
    return fallback


def _safe_number(value: Any, expected: type[int] | type[float]) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return expected(value)
    return None


def _normalize_cover_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    trusted_host = (
        host == "hdslb.com"
        or host.endswith(".hdslb.com")
        or host == "bilibili.com"
        or host.endswith(".bilibili.com")
    )
    try:
        port = parsed.port
    except ValueError as exc:
        raise EngineError("unsafe_cover_url", "封面地址不受信任") from exc
    default_port = 80 if parsed.scheme == "http" else 443
    if (
        parsed.scheme not in {"http", "https"}
        or not trusted_host
        or parsed.username is not None
        or parsed.password is not None
        or (port is not None and port != default_port)
    ):
        raise EngineError("unsafe_cover_url", "封面地址不受信任")
    return urlunsplit(("https", host, parsed.path, parsed.query, ""))


def _safe_cover_preview_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _normalize_cover_url(value)
    except EngineError:
        return None


def _media_stem(resolved: ResolvedVideo, page: VideoPage, request: CreateJobRequest) -> str:
    stem = f"{resolved.title} [{resolved.bvid}]"
    if len(resolved.pages) > 1 and len(request.page_indices) > 1:
        stem += f" - P{page.index:02d} {page.title}"
    return sanitize_filename(stem)


class DownloaderEngine:
    def __init__(self, cookie_store: CookieStore) -> None:
        self.cookie_store = cookie_store

    def _base_options(self, logger: _EngineLogger) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "logger": logger,
            "socket_timeout": 20,
            "retries": 3,
            "fragment_retries": 3,
            "concurrent_fragment_downloads": 4,
        }
        location = ffmpeg_location()
        if location:
            options["ffmpeg_location"] = location
        return options

    def auth_status(self, auth: Any) -> AuthStatus:
        if isinstance(auth, GuestAuth):
            return AuthStatus(state="guest")

        logger = _EngineLogger()
        try:
            with self.cookie_store.yt_dlp_options(auth) as cookie_options:
                options = {
                    **self._base_options(logger),
                    **cookie_options,
                    "skip_download": True,
                    "http_headers": {
                        "Referer": "https://www.bilibili.com/",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 Chrome/138.0.0.0 Safari/537.36"
                        ),
                    },
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    with ydl.urlopen("https://api.bilibili.com/x/web-interface/nav") as response:
                        payload = response.read(256 * 1024 + 1)
        except InvalidCookieFile:
            raise
        except (CookieLoadError, DownloadError) as exc:
            message = logger.last_error or str(exc)
            if "cookie" not in message.lower() and "decrypt" not in message.lower():
                raise EngineError("auth_status_unavailable", "暂时无法检查 Bilibili 登录状态") from exc
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except (RequestError, OSError) as exc:
            raise EngineError("auth_status_unavailable", "暂时无法检查 Bilibili 登录状态") from exc

        if len(payload) > 256 * 1024:
            raise EngineError("auth_status_unavailable", "Bilibili 登录状态响应异常")
        try:
            result = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EngineError("auth_status_unavailable", "Bilibili 登录状态响应异常") from exc
        if not isinstance(result, dict):
            raise EngineError("auth_status_unavailable", "Bilibili 登录状态响应异常")
        data = result.get("data")
        if result.get("code") == -101 or not isinstance(data, dict) or not data.get("isLogin"):
            return AuthStatus(state="inactive")
        if result.get("code") != 0:
            raise EngineError("auth_status_unavailable", "暂时无法检查 Bilibili 登录状态")

        username = str(data.get("uname") or "").strip()[:80] or None
        vip_active = data.get("vipStatus") == 1
        vip_data = data.get("vip_label")
        vip_label = None
        if vip_active and isinstance(vip_data, dict):
            vip_label = str(vip_data.get("text") or "").strip()[:40] or None
        if vip_active and not vip_label:
            vip_label = "大会员"
        return AuthStatus(
            state="active",
            username=username,
            vip_active=vip_active,
            vip_label=vip_label,
        )

    def resolve(self, normalized: NormalizedCredential, auth: Any) -> ResolvedVideo:
        logger = _EngineLogger()
        try:
            with self.cookie_store.yt_dlp_options(auth) as cookie_options:
                options = {
                    **self._base_options(logger),
                    **cookie_options,
                    "skip_download": True,
                    "noplaylist": False,
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    raw = ydl.extract_info(normalized.canonical_url, download=False)
                    info = ydl.sanitize_info(raw)
        except InvalidCookieFile:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except (DownloadError, OSError) as exc:
            raise self._map_error(logger.last_error or str(exc)) from exc

        entries = [entry for entry in info.get("entries") or [] if isinstance(entry, dict)]
        if not entries:
            entries = [info]
        root = entries[0]
        bvid = _extract_bvid(root, normalized.video_id)
        aid_value = root.get("aid") or info.get("aid")
        aid = int(aid_value) if isinstance(aid_value, (int, str)) and str(aid_value).isdigit() else None
        pages: list[VideoPage] = []
        for position, entry in enumerate(entries, start=1):
            index_value = entry.get("playlist_index")
            index = int(index_value) if isinstance(index_value, int) and index_value > 0 else position
            formats = entry.get("formats") if isinstance(entry.get("formats"), list) else []
            pages.append(
                VideoPage(
                    index=index,
                    cid=_safe_number(entry.get("cid"), int),
                    title=str(entry.get("title") or entry.get("fulltitle") or f"P{index}"),
                    duration=_safe_number(entry.get("duration"), float),
                    qualities=self._quality_options(formats),
                )
            )

        selected_page = normalized.selected_page
        if selected_page > len(pages):
            selected_page = 1
        thumbnail = _safe_cover_preview_url(info.get("thumbnail") or root.get("thumbnail"))
        return ResolvedVideo(
            canonical_url=normalized.canonical_url,
            bvid=bvid,
            aid=aid,
            title=str(info.get("title") or root.get("title") or bvid),
            uploader=info.get("uploader") or root.get("uploader"),
            thumbnail=thumbnail,
            duration=_safe_number(info.get("duration") or root.get("duration"), float),
            selected_page=selected_page,
            pages=pages,
        )

    def _quality_options(self, formats: list[dict[str, Any]]) -> list[QualityOption]:
        audio_formats = [
            item
            for item in formats
            if item.get("vcodec") in {None, "none"} and item.get("acodec") not in {None, "none"}
        ]
        def audio_priority(item: dict[str, Any]) -> tuple[bool, bool, float]:
            codec = str(item.get("acodec") or "").lower()
            return (
                codec.startswith(("flac", "alac")),
                codec.startswith(("ec-3", "eac3", "ac-3")),
                float(item.get("abr") or item.get("tbr") or 0),
            )

        best_source_audio = max(audio_formats, key=audio_priority, default=None)
        aac_formats = [item for item in audio_formats if _codec_is_aac(item.get("acodec"))]
        best_aac = max(
            aac_formats,
            key=lambda item: item.get("abr") or item.get("tbr") or 0,
            default=None,
        )

        options: list[QualityOption] = []
        for video in formats:
            if video.get("vcodec") in {None, "none"}:
                continue
            format_id = str(video.get("format_id") or "").strip()
            height = video.get("height")
            if not format_id or not isinstance(height, int) or height <= 0:
                continue
            combined_audio = video.get("acodec") if video.get("acodec") not in {None, "none"} else None
            dynamic_range = str(video.get("dynamic_range") or "SDR").upper()
            preferred = (
                _codec_is_h264(video.get("vcodec"))
                and _is_sdr(dynamic_range)
                and (combined_audio is not None or best_aac is not None)
            )
            audio_codec = combined_audio or (
                (best_aac if preferred else best_source_audio) or {}
            ).get("acodec")
            fps = _safe_number(video.get("fps"), float)
            bitrate = _safe_number(video.get("tbr") or video.get("vbr"), float)
            quality_code = _safe_number(video.get("quality"), int)
            format_name = str(video.get("format") or video.get("format_note") or f"{height}P")
            family = _codec_family(video.get("vcodec"))
            label_parts = [format_name, family]
            if fps and fps > 30:
                label_parts.append(f"{int(fps)}fps")
            if bitrate:
                label_parts.append(f"{bitrate / 1000:.1f} Mbps")
            if not _is_sdr(dynamic_range):
                label_parts.append("Dolby Vision" if dynamic_range == "DV" else dynamic_range)
            options.append(
                QualityOption(
                    id=format_id,
                    label=" · ".join(label_parts),
                    height=height,
                    width=_safe_number(video.get("width"), int),
                    fps=fps,
                    quality_code=quality_code,
                    format_name=format_name,
                    bitrate_kbps=bitrate,
                    dynamic_range=dynamic_range,
                    codec_family=family,
                    video_codec=str(video.get("vcodec") or "unknown"),
                    audio_codec=str(audio_codec) if audio_codec else None,
                    container=str(video.get("ext") or "mp4"),
                    compatibility="preferred" if preferred else "fallback",
                )
            )
        options.sort(
            key=lambda item: (
                item.height,
                item.quality_code or 0,
                item.fps or 0,
                item.compatibility == "preferred",
                item.bitrate_kbps or 0,
            ),
            reverse=True,
        )
        return options

    def download_job(
        self,
        job_id: str,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> list[str]:
        output_dir = ensure_output_directory(request.output_dir)
        temp_root = output_dir / ".bilidown-tmp"
        task_dir = temp_root / job_id
        task_dir.mkdir(parents=True, exist_ok=False)
        try:
            resolved = self.resolve(normalized, request.auth)
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            if request.media_kind == MediaKind.COVER:
                self._download_cover(resolved, task_dir, normalized, cancel_event, progress)
            else:
                page_map = {page.index: page for page in resolved.pages}
                missing = [index for index in request.page_indices if index not in page_map]
                if missing:
                    raise EngineError("invalid_pages", f"分 P 不存在：{', '.join(map(str, missing))}")
                if request.media_kind == MediaKind.VIDEO and request.quality_id:
                    for page_index in request.page_indices:
                        option = next(
                            (item for item in page_map[page_index].qualities if item.id == request.quality_id),
                            None,
                        )
                        if option is None:
                            raise EngineError("invalid_quality", "所选格式并非所有分 P 共同可用")
                        if (
                            request.video_mode == VideoMode.COMPATIBLE_MP4
                            and option.compatibility != "preferred"
                        ):
                            raise EngineError("invalid_quality", "该格式需要使用原始质量模式")
                for page_index in request.page_indices:
                    if cancel_event.is_set():
                        raise DownloadCancelled("cancelled")
                    self._download_page(
                        resolved,
                        page_map[page_index],
                        task_dir,
                        normalized,
                        request,
                        cancel_event,
                        progress,
                    )

            artifacts = [
                path
                for path in task_dir.iterdir()
                if path.is_file() and path.suffix not in {".part", ".ytdl"}
            ]
            if not artifacts:
                raise EngineError("no_output", "下载完成但未找到输出文件")
            moved = [move_without_overwrite(path, output_dir) for path in artifacts]
            progress({"phase": "completed", "percent": 100.0})
            return [str(path) for path in moved]
        except DownloadCancelled:
            raise
        except EngineError:
            raise
        except InvalidCookieFile:
            raise
        except (DownloadError, OSError, httpx.HTTPError) as exc:
            raise self._map_error(str(exc)) from exc
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)
            with contextlib.suppress(OSError):
                temp_root.rmdir()

    def _download_page(
        self,
        resolved: ResolvedVideo,
        page: VideoPage,
        task_dir: Path,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> None:
        logger = _EngineLogger()
        page_url = f"https://www.bilibili.com/video/{resolved.bvid}?p={page.index}"
        stem = _media_stem(resolved, page, request)

        def hook(data: dict[str, Any]) -> None:
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            status = data.get("status")
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes")
            percent = None
            if isinstance(total, (int, float)) and total > 0 and isinstance(downloaded, (int, float)):
                percent = min(100.0, max(0.0, float(downloaded) / float(total) * 100))
            progress(
                {
                    "phase": "postprocessing" if status == "finished" else "downloading",
                    "current_page": page.index,
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "percent": percent,
                    "speed": data.get("speed"),
                    "eta": data.get("eta"),
                }
            )

        options: dict[str, Any] = {
            **self._base_options(logger),
            "noplaylist": True,
            "paths": {"home": str(task_dir), "temp": str(task_dir)},
            "outtmpl": {"default": str(task_dir / f"{stem}.%(ext)s")},
            "progress_hooks": [hook],
            "overwrites": False,
        }
        if request.media_kind == MediaKind.VIDEO:
            if request.quality_id:
                if request.video_mode == VideoMode.SOURCE_AUTO:
                    options["format"] = (
                        f"{request.quality_id}+ba[acodec^=flac]/"
                        f"{request.quality_id}+ba[acodec^=ec-3]/"
                        f"{request.quality_id}+ba/{request.quality_id}"
                    )
                    options["merge_output_format"] = "mp4/mkv"
                else:
                    options["format"] = (
                        f"{request.quality_id}+ba[acodec^=mp4a]/"
                        f"{request.quality_id}+ba[ext=m4a]/{request.quality_id}"
                    )
                    options["merge_output_format"] = "mp4"
            else:
                height = request.quality_height
                options.update(
                    {
                        "format": (
                            f"bv[height={height}][vcodec^=avc1]+ba[acodec^=mp4a]/"
                            f"bv[height={height}]+ba/b[height={height}]"
                        ),
                        "merge_output_format": "mp4",
                    }
                )
        else:
            if request.audio_format == AudioFormat.BEST_SOURCE:
                options["format"] = "ba[acodec^=flac]/ba[acodec^=ec-3]/ba/bestaudio/best"
            elif request.audio_format == AudioFormat.MP3:
                options["format"] = "ba[acodec^=flac]/ba[acodec^=ec-3]/ba/bestaudio/best"
            else:
                options["format"] = "ba[acodec^=mp4a]/ba/bestaudio/best"
            if request.audio_format == AudioFormat.MP3:
                options["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": None,
                    }
                ]
                options["postprocessor_args"] = {
                    "FFmpegExtractAudio+ffmpeg_o": ["-q:a", "2"]
                }

        try:
            with self.cookie_store.yt_dlp_options(request.auth) as cookie_options:
                with yt_dlp.YoutubeDL({**options, **cookie_options}) as ydl:
                    ydl.download([page_url])
        except DownloadCancelled:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except DownloadError as exc:
            raise self._map_error(logger.last_error or str(exc)) from exc

    def _download_cover(
        self,
        resolved: ResolvedVideo,
        task_dir: Path,
        normalized: NormalizedCredential,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> None:
        if not resolved.thumbnail:
            raise EngineError("cover_unavailable", "该视频没有可下载的封面")
        cover_url = _normalize_cover_url(resolved.thumbnail)
        parsed = urlsplit(cover_url)
        headers = {
            "User-Agent": "Mozilla/5.0 Bilidown/0.1",
            "Referer": normalized.canonical_url,
        }
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0), headers=headers) as client:
            with client.stream("GET", cover_url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                extension = mimetypes.guess_extension(content_type) or Path(parsed.path).suffix or ".jpg"
                if extension == ".jpe":
                    extension = ".jpg"
                target = task_dir / f"{sanitize_filename(f'{resolved.title} [{resolved.bvid}] - cover')}{extension}"
                downloaded = 0
                total = int(response.headers.get("content-length") or 0) or None
                with target.open("wb") as output:
                    for chunk in response.iter_bytes(64 * 1024):
                        if cancel_event.is_set():
                            raise DownloadCancelled("cancelled")
                        output.write(chunk)
                        downloaded += len(chunk)
                        progress(
                            {
                                "phase": "downloading",
                                "downloaded_bytes": downloaded,
                                "total_bytes": total,
                                "percent": downloaded / total * 100 if total else None,
                            }
                        )

    def _map_error(self, message: str) -> EngineError:
        safe = redact_message(message)
        lowered = safe.lower()
        if "login" in lowered or "登录" in lowered or "sessdata" in lowered:
            return EngineError("login_required", "该内容需要有效的 Bilibili 登录态")
        if "vip" in lowered or "会员" in lowered:
            return EngineError("membership_required", "所选清晰度需要账户具备相应会员权限")
        if "geo" in lowered or "region" in lowered or "区域" in lowered:
            return EngineError("region_restricted", "该内容受地区限制")
        if "412" in lowered or "429" in lowered or "rate" in lowered:
            return EngineError("rate_limited", "Bilibili 暂时限制了请求，请稍后重试")
        if "cookie" in lowered and ("decrypt" in lowered or "解密" in lowered):
            return EngineError("cookie_decryption_failed", "无法读取浏览器 Cookie，请改用 cookies.txt")
        if "ffmpeg" in lowered:
            return EngineError("ffmpeg_missing", "需要 ffmpeg 才能完成该媒体任务")
        if "unsupported url" in lowered:
            return EngineError("unsupported_video", "该链接不是首版支持的普通投稿")
        return EngineError("download_failed", safe or "下载失败")
