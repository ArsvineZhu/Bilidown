import os

import pytest

from bilidown.cookies import CookieStore
from bilidown.engine import DownloaderEngine
from bilidown.input_parser import normalize_credential
from bilidown.models import BrowserAuth, GuestAuth


KNOWN_SMOKE_VIDEOS = [
    pytest.param("BV1ACNJ6VEwP", 1080, False, id="public-1080p"),
    pytest.param("BV1NGZtBwELa", 2160, True, id="member-4k"),
]


def smoke_auth() -> GuestAuth | BrowserAuth:
    browser = os.getenv("BILIDOWN_SMOKE_BROWSER")
    if browser in {"chrome", "edge", "firefox"}:
        return BrowserAuth(browser=browser)
    return GuestAuth()


@pytest.mark.skipif(not os.getenv("BILIDOWN_SMOKE_URL"), reason="set BILIDOWN_SMOKE_URL to enable")
async def test_resolves_public_bilibili_video() -> None:
    normalized = await normalize_credential(os.environ["BILIDOWN_SMOKE_URL"])
    resolved = DownloaderEngine(CookieStore()).resolve(normalized, GuestAuth())
    assert resolved.bvid.startswith("BV")
    assert resolved.pages
    assert any(page.qualities for page in resolved.pages)


@pytest.mark.skipif(
    os.getenv("BILIDOWN_KNOWN_NETWORK_SMOKE") != "1",
    reason="set BILIDOWN_KNOWN_NETWORK_SMOKE=1 to enable",
)
@pytest.mark.parametrize(("credential", "expected_height", "requires_login"), KNOWN_SMOKE_VIDEOS)
async def test_known_video_quality_ceiling(
    credential: str,
    expected_height: int,
    requires_login: bool,
) -> None:
    auth = smoke_auth()
    normalized = await normalize_credential(credential)
    resolved = DownloaderEngine(CookieStore()).resolve(normalized, auth)
    qualities = [quality for page in resolved.pages for quality in page.qualities]

    assert resolved.thumbnail is not None
    assert resolved.thumbnail.startswith("https://")
    assert qualities
    if requires_login and isinstance(auth, GuestAuth):
        assert max(quality.height for quality in qualities) >= 1080
        return

    assert max(quality.height for quality in qualities) == expected_height
    if expected_height == 2160:
        four_k = [quality for quality in qualities if quality.height == 2160]
        assert {quality.codec_family for quality in four_k} >= {"H.264", "HEVC", "AV1"}
        assert any(quality.dynamic_range == "DV" for quality in four_k)
        assert any(quality.format_name == "1080P 高码率" for quality in qualities)
