import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

from yt_dlp.utils import DownloadError

from bilidown.cookies import CookieStore
from bilidown.engine import DownloaderEngine
from bilidown.input_parser import NormalizedCredential
from bilidown.models import (
    CreateJobRequest,
    GuestAuth,
    MediaKind,
)
from bilidown.progress import ProgressUpdate


class BatchAdapter:
    def extract(
        self,
        _: str,
        __: Mapping[str, object],
        *,
        download: bool = False,
    ) -> object:
        del download
        raise AssertionError("selected resource items do not need another preview")

    def download(
        self,
        _: Sequence[str],
        options: Mapping[str, object],
    ) -> None:
        if options.get("playlist_items") == "2":
            raise DownloadError("Video unavailable")
        paths = options["paths"]
        assert isinstance(paths, dict)
        home = paths["home"]
        assert isinstance(home, str)
        Path(home, "download.mp4").write_bytes(b"media")

    def open_bytes(
        self,
        _: str,
        __: Mapping[str, object],
        *,
        limit: int,
    ) -> bytes:
        del limit
        raise AssertionError("download does not use raw requests")


def test_batch_download_continues_after_item_failure(tmp_path: Path) -> None:
    engine = DownloaderEngine(CookieStore(), BatchAdapter())  # type: ignore[arg-type]
    request = CreateJobRequest(
        credential="https://www.bilibili.com/list/ml1",
        media_kind=MediaKind.VIDEO,
        item_indices=[1, 2, 3],
        quality_height=1080,
        auth=GuestAuth(),
        output_dir=str(tmp_path),
    )
    updates: list[ProgressUpdate] = []

    outcome = engine.download_job(
        "batch-job",
        NormalizedCredential(request.credential, "resource", 1),
        request,
        threading.Event(),
        updates.append,
    )

    assert len(outcome.paths) == 2
    assert [item.status for item in outcome.item_results] == [
        "completed",
        "failed",
        "completed",
    ]
    assert outcome.item_results[1].error_code is not None
    assert all(Path(path).is_file() for path in outcome.paths)
