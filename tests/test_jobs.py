import asyncio
from pathlib import Path

from bilidown.jobs import JobManager
from bilidown.models import CreateJobRequest, GuestAuth, JobStatus, MediaKind


class FakeEngine:
    def download_job(self, job_id, normalized, request, cancel_event, progress):
        progress({"phase": "downloading", "percent": 50.0, "current_page": 1})
        if cancel_event.is_set():
            from yt_dlp.utils import DownloadCancelled

            raise DownloadCancelled("cancelled")
        return [str(Path(request.output_dir) / "video.mp4")]


async def wait_for_terminal(manager: JobManager, job_id: str):
    for _ in range(100):
        job = manager.get(job_id)
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


async def test_job_manager_runs_single_job(tmp_path: Path) -> None:
    manager = JobManager(FakeEngine())  # type: ignore[arg-type]
    await manager.start()
    try:
        request = CreateJobRequest(
            credential="BV1xx411c7mD",
            media_kind=MediaKind.VIDEO,
            page_indices=[1],
            quality_height=720,
            auth=GuestAuth(),
            output_dir=str(tmp_path),
        )
        submitted = await manager.submit(request)
        completed = await wait_for_terminal(manager, submitted.id)
        assert completed.status == JobStatus.COMPLETED
        assert completed.progress.percent == 100
        assert completed.result_paths[0].endswith("video.mp4")
    finally:
        await manager.stop()


async def test_can_cancel_queued_job(tmp_path: Path) -> None:
    manager = JobManager(FakeEngine())  # type: ignore[arg-type]
    request = CreateJobRequest(
        credential="BV1xx411c7mD",
        media_kind=MediaKind.VIDEO,
        page_indices=[1],
        quality_height=720,
        auth=GuestAuth(),
        output_dir=str(tmp_path),
    )
    submitted = await manager.submit(request)
    cancelled = manager.cancel(submitted.id)
    assert cancelled.status == JobStatus.CANCELLED

