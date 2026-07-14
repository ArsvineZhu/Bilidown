from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GuestAuth(BaseModel):
    kind: Literal["guest"] = "guest"


class BrowserAuth(BaseModel):
    kind: Literal["browser"] = "browser"
    browser: Literal["chrome", "edge", "firefox"]
    profile: str | None = Field(default=None, max_length=260)


class CookieSessionAuth(BaseModel):
    kind: Literal["cookie_session"] = "cookie_session"
    session_id: str = Field(min_length=1, max_length=100)


AuthConfig = Annotated[
    GuestAuth | BrowserAuth | CookieSessionAuth,
    Field(discriminator="kind"),
]


class ResolveRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=2048)
    auth: AuthConfig = Field(default_factory=GuestAuth)

    @field_validator("credential")
    @classmethod
    def strip_credential(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("视频凭据不能为空")
        return value


class AuthStatusRequest(BaseModel):
    auth: AuthConfig = Field(default_factory=GuestAuth)


class AuthStatus(BaseModel):
    state: Literal["guest", "active", "inactive"]
    username: str | None = None
    vip_active: bool = False
    vip_label: str | None = None


class QualityOption(BaseModel):
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


class VideoPage(BaseModel):
    index: int
    cid: int | None = None
    title: str
    duration: float | None = None
    qualities: list[QualityOption]


class ResolvedVideo(BaseModel):
    canonical_url: str
    bvid: str
    aid: int | None = None
    title: str
    uploader: str | None = None
    thumbnail: str | None = None
    duration: float | None = None
    selected_page: int = 1
    pages: list[VideoPage]


class MediaKind(StrEnum):
    COVER = "cover"
    AUDIO = "audio"
    VIDEO = "video"


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
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateJobRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=2048)
    media_kind: MediaKind
    page_indices: list[int] = Field(default_factory=list, max_length=100)
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

    @model_validator(mode="after")
    def validate_media_options(self) -> "CreateJobRequest":
        if (
            self.media_kind == MediaKind.VIDEO
            and self.quality_height is None
            and self.quality_id is None
        ):
            raise ValueError("视频任务必须指定清晰度")
        if self.media_kind != MediaKind.COVER and not self.page_indices:
            raise ValueError("音频或视频任务至少选择一个分 P")
        return self


class JobProgress(BaseModel):
    phase: str = "queued"
    current_page: int | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    percent: float | None = None
    speed: float | None = None
    eta: float | None = None


class JobView(BaseModel):
    id: str
    status: JobStatus
    request: CreateJobRequest
    progress: JobProgress = Field(default_factory=JobProgress)
    result_paths: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class AppStatus(BaseModel):
    app_version: str
    yt_dlp_version: str
    ffmpeg_version: str | None
    ffmpeg_available: bool
    default_output_dir: str


class OpenOutputRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
