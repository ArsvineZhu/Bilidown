import json
import threading
from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError

from bilidown.cookies import CookieStore
from bilidown.engine import (
    DownloaderEngine,
    EngineError,
    _media_stem,
    _normalize_cover_url,
    _safe_cover_preview_url,
)
from bilidown.input_parser import NormalizedCredential
from bilidown.models import (
    AudioFormat,
    AuthStatus,
    BrowserAuth,
    CreateJobRequest,
    GuestAuth,
    MediaKind,
    QualityOption,
    ResolvedVideo,
    VideoMode,
    VideoPage,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "http://i0.hdslb.com/bfs/archive/cover.jpg",
            "https://i0.hdslb.com/bfs/archive/cover.jpg",
        ),
        (
            "https://i2.hdslb.com/bfs/archive/cover.jpg?token=value#fragment",
            "https://i2.hdslb.com/bfs/archive/cover.jpg?token=value",
        ),
        (
            "http://www.bilibili.com:80/cover.png",
            "https://www.bilibili.com/cover.png",
        ),
    ],
)
def test_normalize_cover_url_accepts_trusted_bilibili_hosts(source: str, expected: str) -> None:
    assert _normalize_cover_url(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "https://evil.example/cover.jpg",
        "https://hdslb.com.evil.example/cover.jpg",
        "ftp://i0.hdslb.com/cover.jpg",
        "https://user:password@i0.hdslb.com/cover.jpg",
        "https://i0.hdslb.com:8443/cover.jpg",
        "https://i0.hdslb.com:not-a-port/cover.jpg",
    ],
)
def test_normalize_cover_url_rejects_untrusted_urls(source: str) -> None:
    with pytest.raises(EngineError) as exc_info:
        _normalize_cover_url(source)

    assert exc_info.value.code == "unsafe_cover_url"


def test_cover_preview_upgrades_trusted_http_and_drops_untrusted_url() -> None:
    assert _safe_cover_preview_url("http://i0.hdslb.com/cover.jpg") == "https://i0.hdslb.com/cover.jpg"
    assert _safe_cover_preview_url("https://evil.example/cover.jpg") is None


def quality(option_id: str = "30080", *, compatibility: str = "preferred") -> QualityOption:
    return QualityOption(
        id=option_id,
        label="1080P 高清 · H.264 · 2.1 Mbps",
        height=1080,
        width=1920,
        fps=30,
        quality_code=80,
        format_name="1080P 高清",
        bitrate_kbps=2100,
        dynamic_range="SDR",
        codec_family="H.264" if compatibility == "preferred" else "HEVC",
        video_codec="avc1.640033" if compatibility == "preferred" else "hvc1.1.6.L150.90",
        audio_codec="mp4a.40.2",
        container="mp4",
        compatibility=compatibility,  # type: ignore[arg-type]
    )


def resolved_video(page_count: int) -> ResolvedVideo:
    pages = [
        VideoPage(index=index, cid=index, title=f"第 {index} 部分", duration=10, qualities=[quality()])
        for index in range(1, page_count + 1)
    ]
    return ResolvedVideo(
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        title="测试视频",
        pages=pages,
    )


@pytest.mark.parametrize(
    ("page_count", "selected_pages", "expected"),
    [
        (1, [1], "测试视频 [BV1xx411c7mD]"),
        (2, [1], "测试视频 [BV1xx411c7mD]"),
        (2, [2], "测试视频 [BV1xx411c7mD]"),
        (2, [1, 2], "测试视频 [BV1xx411c7mD] - P01 第 1 部分"),
    ],
)
def test_media_stem_only_names_pages_for_multi_page_jobs(
    tmp_path: Path,
    page_count: int,
    selected_pages: list[int],
    expected: str,
) -> None:
    resolved = resolved_video(page_count)
    request = CreateJobRequest(
        credential=resolved.bvid,
        media_kind=MediaKind.AUDIO,
        page_indices=selected_pages,
        audio_format=AudioFormat.M4A,
        output_dir=str(tmp_path),
    )
    assert _media_stem(resolved, resolved.pages[selected_pages[0] - 1], request) == expected


def test_quality_options_preserve_codec_variants_at_same_height() -> None:
    formats = [
        {"format_id": "30280", "vcodec": "none", "acodec": "mp4a.40.2", "tbr": 190, "ext": "m4a"},
        {"format_id": "30080", "quality": 80, "format": "1080P 高清", "height": 1080, "width": 1920, "fps": 30, "vcodec": "avc1.640033", "acodec": "none", "dynamic_range": "SDR", "tbr": 2100, "ext": "mp4"},
        {"format_id": "30077", "quality": 80, "format": "1080P 高清", "height": 1080, "width": 1920, "fps": 30, "vcodec": "hvc1.1.6.L150.90", "acodec": "none", "dynamic_range": "SDR", "tbr": 1100, "ext": "mp4"},
        {"format_id": "100026", "quality": 80, "format": "1080P 高清", "height": 1080, "width": 1920, "fps": 30, "vcodec": "av01.0.08M.08", "acodec": "none", "dynamic_range": "HDR10", "tbr": 900, "ext": "mp4"},
    ]

    options = DownloaderEngine(CookieStore())._quality_options(formats)

    assert {item.id for item in options} == {"30080", "30077", "100026"}
    assert {item.codec_family for item in options} == {"H.264", "HEVC", "AV1"}
    assert next(item for item in options if item.id == "30080").compatibility == "preferred"
    assert "HDR10" in next(item for item in options if item.id == "100026").label


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return self.payload


def fake_ydl(payload: dict[str, object]):
    class FakeYoutubeDL:
        def __init__(self, _: dict[str, object]) -> None:
            return None

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def urlopen(self, _: str) -> FakeResponse:
            return FakeResponse(payload)

    return FakeYoutubeDL


def test_auth_status_reports_nickname_and_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "code": 0,
        "data": {
            "isLogin": True,
            "uname": "测试用户",
            "vipStatus": 1,
            "vip_label": {"text": "年度大会员"},
        },
    }
    monkeypatch.setattr("bilidown.engine.yt_dlp.YoutubeDL", fake_ydl(payload))

    status = DownloaderEngine(CookieStore()).auth_status(BrowserAuth(browser="firefox"))

    assert status.state == "active"
    assert status.username == "测试用户"
    assert status.vip_active is True
    assert status.vip_label == "年度大会员"


def test_auth_status_guest_does_not_make_network_request() -> None:
    assert DownloaderEngine(CookieStore()).auth_status(GuestAuth()).state == "guest"


def test_auto_auth_prefers_edge_then_falls_back_to_chrome(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = DownloaderEngine(CookieStore())
    checked: list[str] = []

    def fake_auth_status(auth: BrowserAuth) -> AuthStatus:
        checked.append(auth.browser)
        if auth.browser == "edge":
            return AuthStatus(state="inactive")
        return AuthStatus(state="active", username="测试用户")

    monkeypatch.setattr(engine, "auth_status", fake_auth_status)

    result = engine.auto_auth()

    assert checked == ["edge", "chrome"]
    assert result.auth == BrowserAuth(browser="chrome")
    assert result.status.username == "测试用户"


def test_auto_auth_falls_back_to_guest_when_browser_cookies_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = DownloaderEngine(CookieStore())

    def fake_auth_status(_: BrowserAuth) -> AuthStatus:
        raise EngineError("cookie_decryption_failed", "无法读取浏览器 Cookie")

    monkeypatch.setattr(engine, "auth_status", fake_auth_status)

    result = engine.auto_auth()

    assert result.auth == GuestAuth()
    assert result.status.state == "guest"


def test_auth_status_maps_browser_cookie_decryption_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingYoutubeDL:
        def __init__(self, _: dict[str, object]) -> None:
            raise DownloadError("Failed to decrypt browser cookies with DPAPI")

    monkeypatch.setattr("bilidown.engine.yt_dlp.YoutubeDL", FailingYoutubeDL)

    with pytest.raises(EngineError) as exc_info:
        DownloaderEngine(CookieStore()).auth_status(BrowserAuth(browser="chrome"))

    assert exc_info.value.code == "cookie_decryption_failed"
    assert "Cookie" in exc_info.value.message


@pytest.mark.parametrize(
    ("mode", "option", "expected_format", "expected_container"),
    [
        (
            VideoMode.COMPATIBLE_MP4,
            quality(),
            "30080+ba[acodec^=mp4a]/30080+ba[ext=m4a]/30080",
            "mp4",
        ),
        (
            VideoMode.SOURCE_AUTO,
            quality("30077", compatibility="fallback"),
            "30077+ba[acodec^=flac]/30077+ba[acodec^=ec-3]/30077+ba/30077",
            "mp4/mkv",
        ),
    ],
)
def test_download_page_uses_exact_format_variant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: VideoMode,
    option: QualityOption,
    expected_format: str,
    expected_container: str,
) -> None:
    captured: list[dict[str, object]] = []

    class CapturingYoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            captured.append(options)

        def __enter__(self) -> "CapturingYoutubeDL":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def download(self, _: list[str]) -> None:
            return None

    monkeypatch.setattr("bilidown.engine.yt_dlp.YoutubeDL", CapturingYoutubeDL)
    page = VideoPage(index=1, cid=1, title="第一部分", duration=10, qualities=[option])
    resolved = ResolvedVideo(
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        title="测试视频",
        pages=[page],
    )
    request = CreateJobRequest(
        credential=resolved.bvid,
        media_kind=MediaKind.VIDEO,
        page_indices=[1],
        quality_id=option.id,
        quality_height=option.height,
        video_mode=mode,
        output_dir=str(tmp_path),
    )

    DownloaderEngine(CookieStore())._download_page(
        resolved,
        page,
        tmp_path,
        NormalizedCredential(resolved.canonical_url, resolved.bvid, 1),
        request,
        threading.Event(),
        lambda _: None,
    )

    assert captured[0]["format"] == expected_format
    assert captured[0]["merge_output_format"] == expected_container


def test_resolve_uses_base_video_url_to_return_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_urls: list[str] = []
    payload = {
        "id": "BV1xx411c7mD",
        "title": "测试合集",
        "uploader": "测试 UP 主",
        "entries": [
            {
                "id": "BV1xx411c7mD_p1",
                "playlist_index": 1,
                "title": "第一部分",
                "duration": 10,
                "formats": [],
            },
            {
                "id": "BV1xx411c7mD_p2",
                "playlist_index": 2,
                "title": "第二部分",
                "duration": 20,
                "formats": [],
            },
        ],
    }

    class FakeYoutubeDL:
        def __init__(self, _: dict[str, object]) -> None:
            return None

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def extract_info(self, url: str, *, download: bool) -> dict[str, object]:
            assert download is False
            captured_urls.append(url)
            return payload

        def sanitize_info(self, info: dict[str, object]) -> dict[str, object]:
            return info

    monkeypatch.setattr("bilidown.engine.yt_dlp.YoutubeDL", FakeYoutubeDL)

    resolved = DownloaderEngine(CookieStore()).resolve(
        NormalizedCredential(
            "https://www.bilibili.com/video/BV1xx411c7mD?p=2",
            "BV1xx411c7mD",
            2,
        ),
        GuestAuth(),
    )

    assert captured_urls == ["https://www.bilibili.com/video/BV1xx411c7mD"]
    assert [page.index for page in resolved.pages] == [1, 2]
    assert resolved.selected_page == 2
