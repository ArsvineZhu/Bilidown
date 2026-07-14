import httpx
import pytest

from bilidown.input_parser import InvalidCredential, normalize_credential


@pytest.mark.parametrize(
    ("credential", "expected"),
    [
        ("BV1xx411c7mD", "https://www.bilibili.com/video/BV1xx411c7mD"),
        ("av170001", "https://www.bilibili.com/video/av170001"),
        (
            "https://www.bilibili.com/video/BV1xx411c7mD?p=2&spm_id_from=test",
            "https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        ),
    ],
)
async def test_normalizes_supported_credentials(credential: str, expected: str) -> None:
    result = await normalize_credential(credential)
    assert result.canonical_url == expected


async def test_resolves_trusted_short_link() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://www.bilibili.com/video/BV1xx411c7mD?p=3"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await normalize_credential("https://b23.tv/example", client=client)
    assert result.selected_page == 3
    assert result.video_id == "BV1xx411c7mD"


async def test_rejects_untrusted_short_link_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/video"}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(InvalidCredential, match="不受信任"):
            await normalize_credential("https://b23.tv/example", client=client)


@pytest.mark.parametrize(
    "credential",
    [
        "170001",
        "http://www.bilibili.com/video/BV1xx411c7mD",
        "https://example.com/video/BV1xx411c7mD",
        "https://www.bilibili.com/bangumi/play/ep1",
    ],
)
async def test_rejects_unsupported_credentials(credential: str) -> None:
    with pytest.raises(InvalidCredential):
        await normalize_credential(credential)

