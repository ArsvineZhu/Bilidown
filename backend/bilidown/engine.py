from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from yt_dlp.cookies import CookieLoadError
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError

from .cookies import CookieStore, InvalidCookieFile
from .download_result import DownloadOutcome
from .errors import EngineError, map_engine_error
from .input_parser import NormalizedCredential
from .media_download import MediaDownloadService
from .media_metadata import (
    media_stem,
    normalize_cover_url,
    quality_options,
    resolved_video_from_info,
    safe_cover_preview_url,
)
from .models import (
    AuthConfig,
    AuthStatus,
    AutoAuthResult,
    BrowserAuth,
    CreateJobRequest,
    GuestAuth,
    QualityOption,
    ResolvedResource,
    ResolvedVideo,
    VideoPage,
)
from .progress import ProgressCallback
from .resource_resolver import ResourceResolver
from .runtime import ffmpeg_location
from .yt_adapter import DEFAULT_YT_ADAPTER, YtDlpAdapter
from .yt_logging import EngineLogger


_normalize_cover_url = normalize_cover_url
_safe_cover_preview_url = safe_cover_preview_url
_media_stem = media_stem


class _VipLabel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class _AuthData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    is_login: bool = Field(default=False, alias="isLogin")
    username: str | None = Field(default=None, alias="uname")
    vip_status: int = Field(default=0, alias="vipStatus")
    vip_label: _VipLabel | None = None


class _AuthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: int
    data: _AuthData | None = None


class DownloaderEngine:
    def __init__(
        self,
        cookie_store: CookieStore,
        adapter: YtDlpAdapter = DEFAULT_YT_ADAPTER,
    ) -> None:
        self.cookie_store = cookie_store
        self._adapter = adapter
        self._resources = ResourceResolver(
            cookie_store,
            adapter,
            self._base_options,
        )
        self._downloads = MediaDownloadService(
            cookie_store,
            adapter,
            self._base_options,
            self.resolve,
        )

    @staticmethod
    def _base_options(logger: EngineLogger) -> dict[str, object]:
        options: dict[str, object] = {
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

    def auth_status(self, auth: AuthConfig) -> AuthStatus:
        if isinstance(auth, GuestAuth):
            return AuthStatus(state="guest")

        logger = EngineLogger()
        try:
            with self.cookie_store.yt_dlp_options(auth) as cookie_options:
                options: dict[str, object] = {
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
                payload = self._adapter.open_bytes(
                    "https://api.bilibili.com/x/web-interface/nav",
                    options,
                    limit=256 * 1024 + 1,
                )
        except InvalidCookieFile:
            raise
        except (CookieLoadError, DownloadError) as exc:
            message = logger.last_error or str(exc)
            if "cookie" not in message.lower() and "decrypt" not in message.lower():
                raise EngineError(
                    "auth_status_unavailable",
                    "暂时无法检查 Bilibili 登录状态",
                ) from exc
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except (RequestError, OSError) as exc:
            raise EngineError(
                "auth_status_unavailable",
                "暂时无法检查 Bilibili 登录状态",
            ) from exc

        if len(payload) > 256 * 1024:
            raise EngineError("auth_status_unavailable", "Bilibili 登录状态响应异常")
        try:
            result = _AuthResponse.model_validate_json(payload)
        except ValidationError as exc:
            raise EngineError(
                "auth_status_unavailable",
                "Bilibili 登录状态响应异常",
            ) from exc

        if result.code == -101 or result.data is None or not result.data.is_login:
            return AuthStatus(state="inactive")
        if result.code != 0:
            raise EngineError(
                "auth_status_unavailable",
                "暂时无法检查 Bilibili 登录状态",
            )
        username = (result.data.username or "").strip()[:80] or None
        vip_active = result.data.vip_status == 1
        vip_label = None
        if vip_active and result.data.vip_label is not None:
            vip_label = (result.data.vip_label.text or "").strip()[:40] or None
        if vip_active and not vip_label:
            vip_label = "大会员"
        return AuthStatus(
            state="active",
            username=username,
            vip_active=vip_active,
            vip_label=vip_label,
        )

    def auto_auth(self) -> AutoAuthResult:
        for browser_name in ("edge", "chrome", "firefox"):
            browser: BrowserAuth
            if browser_name == "edge":
                browser = BrowserAuth(browser="edge")
            elif browser_name == "chrome":
                browser = BrowserAuth(browser="chrome")
            else:
                browser = BrowserAuth(browser="firefox")
            try:
                status = self.auth_status(browser)
            except EngineError:
                continue
            if status.state == "active":
                return AutoAuthResult(auth=browser, status=status)
        return AutoAuthResult(auth=GuestAuth(), status=AuthStatus(state="guest"))

    def resolve(
        self,
        normalized: NormalizedCredential,
        auth: AuthConfig,
    ) -> ResolvedVideo:
        logger = EngineLogger()
        try:
            with self.cookie_store.yt_dlp_options(auth) as cookie_options:
                options: dict[str, object] = {
                    **self._base_options(logger),
                    **cookie_options,
                    "skip_download": True,
                    "noplaylist": False,
                }
                parsed = urlsplit(normalized.canonical_url)
                anthology_url = urlunsplit(
                    (parsed.scheme, parsed.netloc, parsed.path, "", "")
                )
                info = self._adapter.extract(anthology_url, options)
        except InvalidCookieFile:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except (DownloadError, OSError) as exc:
            raise map_engine_error(logger.last_error or str(exc)) from exc
        return resolved_video_from_info(info, normalized)

    def resolve_resource(
        self,
        canonical_url: str,
        auth: AuthConfig,
    ) -> ResolvedResource:
        return self._resources.resolve(canonical_url, auth)

    @staticmethod
    def _quality_options(
        formats: list[dict[str, object]],
    ) -> list[QualityOption]:
        return quality_options(formats)

    def download_job(
        self,
        job_id: str,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> DownloadOutcome:
        return self._downloads.download_job(
            job_id,
            normalized,
            request,
            cancel_event,
            progress,
        )

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
        self._downloads.download_page(
            resolved,
            page,
            task_dir,
            normalized,
            request,
            cancel_event,
            progress,
        )

    @staticmethod
    def _map_error(message: str) -> EngineError:
        return map_engine_error(message)
