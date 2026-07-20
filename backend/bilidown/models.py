from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class GuestAuth(ApiModel):
    kind: Literal["guest"] = "guest"


class BrowserAuth(ApiModel):
    kind: Literal["browser"] = "browser"
    browser: Literal["chrome", "edge", "firefox"]
    profile: str | None = Field(default=None, max_length=260)


class CookieSessionAuth(ApiModel):
    kind: Literal["cookie_session"] = "cookie_session"
    session_id: str = Field(min_length=1, max_length=100)


AuthConfig = Annotated[
    GuestAuth | BrowserAuth | CookieSessionAuth,
    Field(discriminator="kind"),
]


class ResolveRequest(ApiModel):
    credential: str = Field(min_length=1, max_length=2048)
    auth: AuthConfig = Field(default_factory=GuestAuth)

    @field_validator("credential")
    @classmethod
    def strip_credential(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("视频凭据不能为空")
        return value


class ResourceResolveRequest(ResolveRequest):
    pass


class AuthStatusRequest(ApiModel):
    auth: AuthConfig = Field(default_factory=GuestAuth)


class AuthStatus(ApiModel):
    state: Literal["guest", "active", "inactive"]
    username: str | None = None
    vip_active: bool = False
    vip_label: str | None = None


class AutoAuthResult(ApiModel):
    auth: AuthConfig
    status: AuthStatus


class QualityOption(ApiModel):
    id: str
    label: str
    height: int
    width: int | None = None
    fps: float | None = None
    quality_code: int | None = None
    format_name: str
    bitrate_kbps: float | None = None
    dynamic_range: str | None = None
    codec_family: Literal["H.264", "HEVC", "AV1", "Other"]
    video_codec: str
    audio_codec: str | None = None
    container: str
    compatibility: Literal["preferred", "fallback"] = "fallback"


class VideoPage(ApiModel):
    index: int
    cid: int | None = None
    title: str
    duration: float | None = None
    qualities: list[QualityOption]


class ResolvedVideo(ApiModel):
    canonical_url: str
    bvid: str
    aid: int | None = None
    title: str
    uploader: str | None = None
    thumbnail: str | None = None
    duration: float | None = None
    selected_page: int = 1
    pages: list[VideoPage]


class ResourceKind(StrEnum):
    VIDEO = "video"
    INTERACTIVE = "interactive"
    BANGUMI = "bangumi"
    COURSE = "course"
    FAVORITES = "favorites"
    COLLECTION = "collection"
    SERIES = "series"
    PLAYLIST = "playlist"
    WATCH_LATER = "watch_later"
    SPACE = "space"
    AUDIO = "audio"
    DYNAMIC = "dynamic"
    LIVE = "live"
    INTERNATIONAL = "international"
    CATEGORY = "category"
    SEARCH = "search"
    UNKNOWN = "unknown"


class ResourceItem(ApiModel):
    index: int = Field(ge=1)
    id: str
    url: str
    title: str
    uploader: str | None = None
    duration: float | None = None
    thumbnail: str | None = None
    selected: bool = True
    live: bool = False
    branch: bool = False


class ResolvedResource(ApiModel):
    canonical_url: str
    kind: ResourceKind
    title: str
    uploader: str | None = None
    thumbnail: str | None = None
    items: list[ResourceItem]
    total_items: int
    truncated: bool = False
    experimental: bool = False
    warnings: list[str] = Field(default_factory=list)
    video: ResolvedVideo | None = None


class MediaKind(StrEnum):
    COVER = "cover"
    AUDIO = "audio"
    VIDEO = "video"
    SUBTITLES = "subtitles"
    DANMAKU_XML = "danmaku_xml"
    DANMAKU_ASS = "danmaku_ass"


class AudioFormat(StrEnum):
    ORIGINAL = "original"
    BEST_SOURCE = "best_source"
    M4A = "m4a"
    MP3 = "mp3"


class VideoMode(StrEnum):
    COMPATIBLE_MP4 = "compatible_mp4"
    SOURCE_AUTO = "source_auto"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateJobRequest(ApiModel):
    credential: str = Field(min_length=1, max_length=2048)
    media_kind: MediaKind
    page_indices: list[int] = Field(default_factory=list, max_length=100)
    item_urls: list[str] = Field(default_factory=list, max_length=100)
    item_indices: list[int] = Field(default_factory=list, max_length=100)
    quality_height: int | None = Field(default=None, ge=1, le=10000)
    quality_id: str | None = Field(default=None, min_length=1, max_length=100)
    video_mode: VideoMode = VideoMode.COMPATIBLE_MP4
    audio_format: AudioFormat = AudioFormat.ORIGINAL
    auth: AuthConfig = Field(default_factory=GuestAuth)
    output_dir: str = Field(min_length=1, max_length=1000)

    @field_validator("credential", "output_dir")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("page_indices")
    @classmethod
    def unique_pages(cls, value: list[int]) -> list[int]:
        if any(index < 1 for index in value):
            raise ValueError("分 P 序号必须从 1 开始")
        return list(dict.fromkeys(value))

    @field_validator("item_urls")
    @classmethod
    def unique_item_urls(cls, value: list[str]) -> list[str]:
        stripped = [url.strip() for url in value]
        if any(not url for url in stripped):
            raise ValueError("批量任务链接不能为空")
        return list(dict.fromkeys(stripped))

    @field_validator("item_indices")
    @classmethod
    def unique_item_indices(cls, value: list[int]) -> list[int]:
        if any(index < 1 for index in value):
            raise ValueError("批量条目序号必须从 1 开始")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_media_options(self) -> "CreateJobRequest":
        if (
            self.media_kind == MediaKind.VIDEO
            and self.quality_height is None
            and self.quality_id is None
        ):
            raise ValueError("视频任务必须指定清晰度")
        if (
            not self.item_urls
            and not self.item_indices
            and self.media_kind != MediaKind.COVER
            and not self.page_indices
        ):
            raise ValueError("媒体任务至少选择一个条目或分 P")
        return self


class JobProgress(ApiModel):
    phase: str = "queued"
    current_page: int | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    percent: float | None = None
    speed: float | None = None
    eta: float | None = None


class JobItemResult(ApiModel):
    url: str
    status: Literal["completed", "failed"]
    result_paths: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class JobView(ApiModel):
    id: str
    status: JobStatus
    request: CreateJobRequest
    progress: JobProgress = Field(default_factory=JobProgress)
    result_paths: list[str] = Field(default_factory=list)
    item_results: list[JobItemResult] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class AppStatus(ApiModel):
    app_version: str
    yt_dlp_version: str
    ffmpeg_version: str | None
    ffmpeg_available: bool
    default_output_dir: str


class OpenOutputRequest(ApiModel):
    path: str = Field(min_length=1, max_length=1000)


class CookieSessionResult(ApiModel):
    session_id: str
    cookie_count: int
