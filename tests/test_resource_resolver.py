from collections.abc import Mapping, Sequence

from bilidown.cookies import CookieStore
from bilidown.models import GuestAuth, ResourceKind
from bilidown.resource_resolver import ResourceResolver
from bilidown.yt_logging import EngineLogger


class FakeAdapter:
    def __init__(self, result: object) -> None:
        self.result = result
        self.options: Mapping[str, object] = {}

    def extract(
        self,
        _: str,
        options: Mapping[str, object],
        *,
        download: bool = False,
    ) -> object:
        assert download is False
        self.options = options
        return self.result

    def download(
        self,
        _: Sequence[str],
        __: Mapping[str, object],
    ) -> None:
        raise AssertionError("preview must not download")

    def open_bytes(
        self,
        _: str,
        __: Mapping[str, object],
        *,
        limit: int,
    ) -> bytes:
        del limit
        raise AssertionError("preview must not open raw bytes")


def base_options(_: EngineLogger) -> dict[str, object]:
    return {"quiet": True}


def test_resolves_favorites_as_bounded_preview() -> None:
    entries = [
        {
            "id": f"BV00000000{index:02d}",
            "title": f"视频 {index}",
            "url": f"https://www.bilibili.com/video/BV00000000{index:02d}",
        }
        for index in range(1, 102)
    ]
    adapter = FakeAdapter(
        {
            "extractor_key": "BilibiliFavoritesList",
            "title": "收藏夹",
            "playlist_count": 150,
            "entries": entries,
        }
    )
    resolver = ResourceResolver(CookieStore(), adapter, base_options)  # type: ignore[arg-type]

    resource = resolver.resolve(
        "https://www.bilibili.com/medialist/detail/ml1",
        GuestAuth(),
    )

    assert resource.kind == ResourceKind.FAVORITES
    assert len(resource.items) == 100
    assert resource.total_items == 150
    assert resource.truncated is True
    assert adapter.options["playlistend"] == 101


def test_marks_interactive_nodes_and_documents_limitation() -> None:
    adapter = FakeAdapter(
        {
            "extractor_key": "BiliBili",
            "title": "互动视频",
            "entries": [
                {
                    "id": "BV1xx411c7mD_123",
                    "title": "分支节点",
                    "url": "https://www.bilibili.com/video/BV1xx411c7mD",
                }
            ],
        }
    )
    resolver = ResourceResolver(CookieStore(), adapter, base_options)  # type: ignore[arg-type]

    resource = resolver.resolve(
        "https://www.bilibili.com/video/BV1xx411c7mD",
        GuestAuth(),
    )

    assert resource.kind == ResourceKind.INTERACTIVE
    assert resource.items[0].branch is True
    assert "interactive_paths" in resource.warnings
