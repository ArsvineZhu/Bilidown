from __future__ import annotations

import contextlib
import mimetypes
import shutil
import threading
from collections.abc import Callable
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

import httpx
from yt_dlp.cookies import CookieLoadError
from yt_dlp.utils import DownloadCancelled, DownloadError

from .cookies import CookieStore, InvalidCookieFile
from .danmaku import convert_xml_to_ass
from .download_result import DownloadOutcome
from .errors import EngineError, map_engine_error
from .files import ensure_output_directory, move_without_overwrite, sanitize_filename
from .input_parser import NormalizedCredential
from .media_metadata import media_stem, normalize_cover_url
from .models import (
    AudioFormat,
    AuthConfig,
    CreateJobRequest,
    JobItemResult,
    MediaKind,
    ResolvedVideo,
    VideoMode,
    VideoPage,
)
from .progress import ProgressCallback, ProgressUpdate
from .typeguards import as_float, as_int, as_mapping, as_str
from .yt_adapter import YtDlpAdapter
from .yt_logging import EngineLogger


BaseOptionsFactory = Callable[[EngineLogger], dict[str, object]]
ResolveCallback = Callable[[NormalizedCredential, AuthConfig], ResolvedVideo]


class MediaDownloadService:
    def __init__(
        self,
        cookie_store: CookieStore,
        adapter: YtDlpAdapter,
        base_options: BaseOptionsFactory,
        resolve: ResolveCallback,
    ) -> None:
        self._cookie_store = cookie_store
        self._adapter = adapter
        self._base_options = base_options
        self._resolve = resolve

    def download_job(
        self,
        job_id: str,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> DownloadOutcome:
        output_dir = ensure_output_directory(request.output_dir)
        temp_root = output_dir / ".bilidown-tmp"
        task_dir = temp_root / job_id
        task_dir.mkdir(parents=True, exist_ok=False)
        try:
            if request.item_indices or request.item_urls:
                return self._download_resource_items(
                    normalized.canonical_url,
                    task_dir,
                    output_dir,
                    request,
                    cancel_event,
                    progress,
                )
            resolved = self._resolve(normalized, request.auth)
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            if request.media_kind == MediaKind.COVER:
                self._download_cover(
                    resolved,
                    task_dir,
                    normalized,
                    cancel_event,
                    progress,
                )
            else:
                self._download_selected_pages(
                    resolved,
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
            progress(ProgressUpdate(phase="completed", percent=100.0))
            return DownloadOutcome(paths=[str(path) for path in moved])
        except (DownloadCancelled, EngineError, InvalidCookieFile):
            raise
        except (DownloadError, OSError, httpx.HTTPError) as exc:
            raise map_engine_error(str(exc)) from exc
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)
            with contextlib.suppress(OSError):
                temp_root.rmdir()

    def _download_resource_items(
        self,
        source_url: str,
        task_dir: Path,
        output_dir: Path,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> DownloadOutcome:
        targets = (
            [(source_url, index) for index in request.item_indices]
            if request.item_indices
            else [(url, None) for url in request.item_urls]
        )
        moved_paths: list[str] = []
        results: list[JobItemResult] = []
        for position, (url, playlist_index) in enumerate(targets, start=1):
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            item_dir = task_dir / f"item-{position:03d}"
            item_dir.mkdir()
            item_label = (
                f"{source_url}#item-{playlist_index}"
                if playlist_index is not None
                else url
            )
            try:
                self._download_resource_item(
                    url,
                    playlist_index,
                    item_dir,
                    request,
                    cancel_event,
                    progress,
                    position,
                )
                artifacts = [
                    path
                    for path in item_dir.rglob("*")
                    if path.is_file() and path.suffix not in {".part", ".ytdl"}
                ]
                if request.media_kind == MediaKind.DANMAKU_ASS:
                    xml_files = [
                        path for path in artifacts if path.suffix.lower() == ".xml"
                    ]
                    for xml_path in xml_files:
                        ass_path = xml_path.with_suffix(".ass")
                        convert_xml_to_ass(xml_path, ass_path)
                        xml_path.unlink()
                    artifacts = [
                        path
                        for path in item_dir.rglob("*")
                        if path.is_file()
                        and path.suffix not in {".part", ".ytdl", ".xml"}
                    ]
                if not artifacts:
                    raise EngineError(
                        "no_output",
                        "该条目下载完成但未找到输出文件",
                    )
                moved = [
                    move_without_overwrite(path, output_dir)
                    for path in artifacts
                ]
                paths = [str(path) for path in moved]
                moved_paths.extend(paths)
                results.append(
                    JobItemResult(
                        url=item_label,
                        status="completed",
                        result_paths=paths,
                    )
                )
            except DownloadCancelled:
                raise
            except InvalidCookieFile:
                raise
            except EngineError as exc:
                results.append(
                    JobItemResult(
                        url=item_label,
                        status="failed",
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                )
            except (CookieLoadError, DownloadError, OSError, ValueError) as exc:
                mapped = map_engine_error(str(exc))
                results.append(
                    JobItemResult(
                        url=item_label,
                        status="failed",
                        error_code=mapped.code,
                        error_message=mapped.message,
                    )
                )
            finally:
                shutil.rmtree(item_dir, ignore_errors=True)
            progress(
                ProgressUpdate(
                    phase="downloading",
                    current_page=position,
                    percent=position / len(targets) * 100,
                )
            )
        if not moved_paths:
            first_error = next(
                (item for item in results if item.error_message),
                None,
            )
            error_code = (
                first_error.error_code
                if first_error and first_error.error_code
                else "no_output"
            )
            error_message = (
                first_error.error_message
                if first_error and first_error.error_message
                else "所有条目均下载失败"
            )
            raise EngineError(
                error_code,
                error_message,
            )
        progress(ProgressUpdate(phase="completed", percent=100.0))
        return DownloadOutcome(paths=moved_paths, item_results=results)

    def _download_resource_item(
        self,
        url: str,
        playlist_index: int | None,
        task_dir: Path,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
        current_item: int,
    ) -> None:
        logger = EngineLogger()

        def hook(raw_update: object) -> None:
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            update = as_mapping(raw_update)
            if update is None:
                return
            total = as_float(update.get("total_bytes")) or as_float(
                update.get("total_bytes_estimate")
            )
            downloaded = as_float(update.get("downloaded_bytes"))
            percent = (
                min(100.0, max(0.0, downloaded / total * 100))
                if total and downloaded is not None
                else None
            )
            value = ProgressUpdate(
                phase=(
                    "postprocessing"
                    if as_str(update.get("status")) == "finished"
                    else "downloading"
                ),
                current_page=current_item,
            )
            if percent is not None:
                value["percent"] = percent
            progress(value)

        options: dict[str, object] = {
            **self._base_options(logger),
            "noplaylist": playlist_index is None,
            "paths": {"home": str(task_dir), "temp": str(task_dir)},
            "outtmpl": {
                "default": str(
                    task_dir
                    / "%(playlist_index)03d - %(title).150B [%(id)s].%(ext)s"
                )
            },
            "progress_hooks": [hook],
            "overwrites": False,
        }
        if playlist_index is not None:
            options["playlist_items"] = str(playlist_index)
        self._apply_resource_options(options, request)
        try:
            with self._cookie_store.yt_dlp_options(request.auth) as cookie_options:
                self._adapter.download([url], {**options, **cookie_options})
        except DownloadCancelled:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请使用应用内一键登录或 cookies.txt",
            ) from exc
        except DownloadError as exc:
            raise map_engine_error(logger.last_error or str(exc)) from exc

    @staticmethod
    def _apply_resource_options(
        options: dict[str, object],
        request: CreateJobRequest,
    ) -> None:
        if request.media_kind == MediaKind.COVER:
            options.update(
                {
                    "skip_download": True,
                    "writethumbnail": True,
                    "write_all_thumbnails": False,
                }
            )
            return
        if request.media_kind == MediaKind.SUBTITLES:
            options.update(
                {
                    "skip_download": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["all", "-danmaku"],
                    "subtitlesformat": "srt/best",
                }
            )
            return
        if request.media_kind in {
            MediaKind.DANMAKU_XML,
            MediaKind.DANMAKU_ASS,
        }:
            options.update(
                {
                    "skip_download": True,
                    "writesubtitles": True,
                    "subtitleslangs": ["danmaku"],
                    "subtitlesformat": "best",
                }
            )
            return
        MediaDownloadService._apply_format_options(options, request)

    def _download_selected_pages(
        self,
        resolved: ResolvedVideo,
        task_dir: Path,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> None:
        page_map = {page.index: page for page in resolved.pages}
        missing = [index for index in request.page_indices if index not in page_map]
        if missing:
            missing_text = ", ".join(map(str, missing))
            raise EngineError("invalid_pages", f"分 P 不存在：{missing_text}")
        if request.media_kind == MediaKind.VIDEO and request.quality_id:
            for page_index in request.page_indices:
                option = next(
                    (
                        item
                        for item in page_map[page_index].qualities
                        if item.id == request.quality_id
                    ),
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
            self.download_page(
                resolved,
                page_map[page_index],
                task_dir,
                normalized,
                request,
                cancel_event,
                progress,
            )

    def download_page(
        self,
        resolved: ResolvedVideo,
        page: VideoPage,
        task_dir: Path,
        normalized: NormalizedCredential,
        request: CreateJobRequest,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> None:
        del normalized
        logger = EngineLogger()
        page_url = f"https://www.bilibili.com/video/{resolved.bvid}?p={page.index}"
        stem = media_stem(resolved, page, request)

        def hook(raw_update: object) -> None:
            if cancel_event.is_set():
                raise DownloadCancelled("cancelled")
            update = as_mapping(raw_update)
            if update is None:
                return
            total = as_float(update.get("total_bytes")) or as_float(
                update.get("total_bytes_estimate")
            )
            downloaded = as_float(update.get("downloaded_bytes"))
            percent: float | None = None
            if total is not None and total > 0 and downloaded is not None:
                percent = min(100.0, max(0.0, downloaded / total * 100))
            progress_update = ProgressUpdate(
                phase=(
                    "postprocessing"
                    if as_str(update.get("status")) == "finished"
                    else "downloading"
                ),
                current_page=page.index,
            )
            downloaded_int = as_int(update.get("downloaded_bytes"))
            total_int = as_int(update.get("total_bytes")) or as_int(
                update.get("total_bytes_estimate")
            )
            speed = as_float(update.get("speed"))
            eta = as_float(update.get("eta"))
            if downloaded_int is not None:
                progress_update["downloaded_bytes"] = downloaded_int
            if total_int is not None:
                progress_update["total_bytes"] = total_int
            if percent is not None:
                progress_update["percent"] = percent
            if speed is not None:
                progress_update["speed"] = speed
            if eta is not None:
                progress_update["eta"] = eta
            progress(progress_update)

        options: dict[str, object] = {
            **self._base_options(logger),
            "noplaylist": True,
            "paths": {"home": str(task_dir), "temp": str(task_dir)},
            "outtmpl": {"default": str(task_dir / f"{stem}.%(ext)s")},
            "progress_hooks": [hook],
            "overwrites": False,
        }
        self._apply_format_options(options, request)
        try:
            with self._cookie_store.yt_dlp_options(request.auth) as cookie_options:
                self._adapter.download(
                    [page_url],
                    {**options, **cookie_options},
                )
        except DownloadCancelled:
            raise
        except CookieLoadError as exc:
            raise EngineError(
                "cookie_decryption_failed",
                "无法读取浏览器 Cookie，请关闭浏览器后重试或改用 cookies.txt",
            ) from exc
        except DownloadError as exc:
            raise map_engine_error(logger.last_error or str(exc)) from exc

    @staticmethod
    def _apply_format_options(
        options: dict[str, object],
        request: CreateJobRequest,
    ) -> None:
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
                return
            height = request.quality_height
            options["format"] = (
                f"bv*[height<={height}][vcodec^=avc1]+ba[acodec^=mp4a]/"
                f"bv*[height<={height}]+ba/b[height<={height}]/best"
            )
            options["merge_output_format"] = "mp4"
            return

        if request.audio_format == AudioFormat.BEST_SOURCE:
            options["format"] = "ba[acodec^=flac]/ba[acodec^=ec-3]/ba/bestaudio/best"
        elif request.audio_format == AudioFormat.MP3:
            options["format"] = "ba[acodec^=flac]/ba[acodec^=ec-3]/ba/bestaudio/best"
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
        else:
            options["format"] = "ba[acodec^=mp4a]/ba/bestaudio/best"

    @staticmethod
    def _download_cover(
        resolved: ResolvedVideo,
        task_dir: Path,
        normalized: NormalizedCredential,
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> None:
        if not resolved.thumbnail:
            raise EngineError("cover_unavailable", "该视频没有可下载的封面")
        cover_url = normalize_cover_url(resolved.thumbnail)
        parsed = urlsplit(cover_url)
        headers = {
            "User-Agent": "Mozilla/5.0 Bilidown/0.1",
            "Referer": normalized.canonical_url,
        }
        timeout = httpx.Timeout(30.0, connect=10.0)
        with httpx.Client(timeout=timeout, headers=headers) as client:
            with client.stream("GET", cover_url) as response:
                response.raise_for_status()
                raw_content_type = cast(
                    str,
                    response.headers.get("content-type", ""),
                )
                content_type = raw_content_type.split(";", 1)[0]
                extension = (
                    mimetypes.guess_extension(content_type)
                    or Path(parsed.path).suffix
                    or ".jpg"
                )
                if extension == ".jpe":
                    extension = ".jpg"
                filename = sanitize_filename(
                    f"{resolved.title} [{resolved.bvid}] - cover"
                )
                target = task_dir / f"{filename}{extension}"
                downloaded = 0
                total = as_int(
                    cast(str | None, response.headers.get("content-length"))
                )
                with target.open("wb") as output:
                    for chunk in response.iter_bytes(64 * 1024):
                        if cancel_event.is_set():
                            raise DownloadCancelled("cancelled")
                        output.write(chunk)
                        downloaded += len(chunk)
                        update = ProgressUpdate(
                            phase="downloading",
                            downloaded_bytes=downloaded,
                        )
                        if total is not None:
                            update["total_bytes"] = total
                            update["percent"] = downloaded / total * 100
                        progress(update)
