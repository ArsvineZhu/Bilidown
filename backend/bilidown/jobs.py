from __future__ import annotations

import asyncio
import contextlib
import copy
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from yt_dlp.utils import DownloadCancelled

from .cookies import InvalidCookieFile
from .engine import DownloaderEngine, EngineError
from .input_parser import InvalidCredential, NormalizedCredential, normalize_credential
from .models import CreateJobRequest, JobProgress, JobStatus, JobView


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class _JobRecord:
    id: str
    request: CreateJobRequest
    normalized: NormalizedCredential
    status: JobStatus = JobStatus.QUEUED
    progress: JobProgress = field(default_factory=JobProgress)
    result_paths: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    version: int = 0
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def view(self) -> JobView:
        return JobView(
            id=self.id,
            status=self.status,
            request=self.request,
            progress=copy.deepcopy(self.progress),
            result_paths=list(self.result_paths),
            error_code=self.error_code,
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class JobManager:
    def __init__(self, engine: DownloaderEngine) -> None:
        self.engine = engine
        self._jobs: dict[str, _JobRecord] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self._worker_task is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._worker_task = asyncio.create_task(self._worker(), name="bilidown-job-worker")

    async def stop(self) -> None:
        for record in self._jobs.values():
            if record.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                record.cancel_event.set()
        if self._worker_task is not None:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

    async def submit(self, request: CreateJobRequest) -> JobView:
        normalized = await normalize_credential(request.credential)
        record = _JobRecord(id=uuid.uuid4().hex, request=request, normalized=normalized)
        self._jobs[record.id] = record
        await self._queue.put(record.id)
        return record.view()

    async def retry(self, job_id: str) -> JobView:
        record = self._require(job_id)
        if record.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
            raise ValueError("只有失败或取消的任务可以重试")
        return await self.submit(record.request.model_copy(deep=True))

    def get(self, job_id: str) -> JobView:
        return self._require(job_id).view()

    def get_version(self, job_id: str) -> int:
        return self._require(job_id).version

    def list(self) -> list[JobView]:
        return [record.view() for record in reversed(self._jobs.values())]

    def cancel(self, job_id: str) -> JobView:
        record = self._require(job_id)
        if record.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return record.view()
        record.cancel_event.set()
        if record.status == JobStatus.QUEUED:
            self._update_record(record, status=JobStatus.CANCELLED, phase="cancelled")
        return record.view()

    def _require(self, job_id: str) -> _JobRecord:
        record = self._jobs.get(job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            record = self._jobs.get(job_id)
            try:
                if record is None or record.status == JobStatus.CANCELLED:
                    continue
                self._update_record(record, status=JobStatus.RUNNING, phase="resolving")

                def progress(update: dict[str, object]) -> None:
                    if self._loop is not None:
                        self._loop.call_soon_threadsafe(self._apply_progress, job_id, update)

                try:
                    paths = await asyncio.to_thread(
                        self.engine.download_job,
                        record.id,
                        record.normalized,
                        record.request,
                        record.cancel_event,
                        progress,
                    )
                except DownloadCancelled:
                    self._update_record(record, status=JobStatus.CANCELLED, phase="cancelled")
                except InvalidCookieFile as exc:
                    self._update_record(
                        record,
                        status=JobStatus.FAILED,
                        phase="failed",
                        error_code="invalid_cookie",
                        error_message=str(exc),
                    )
                except EngineError as exc:
                    self._update_record(
                        record,
                        status=JobStatus.FAILED,
                        phase="failed",
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                except Exception:
                    self._update_record(
                        record,
                        status=JobStatus.FAILED,
                        phase="failed",
                        error_code="internal_error",
                        error_message="任务执行失败，请展开诊断信息或重试",
                    )
                else:
                    record.result_paths = paths
                    self._update_record(
                        record,
                        status=JobStatus.COMPLETED,
                        phase="completed",
                        percent=100.0,
                    )
            finally:
                self._queue.task_done()

    def _apply_progress(self, job_id: str, update: dict[str, object]) -> None:
        record = self._jobs.get(job_id)
        if record is None or record.status != JobStatus.RUNNING:
            return
        allowed = {
            key: value
            for key, value in update.items()
            if key in JobProgress.model_fields and value is not None
        }
        self._update_record(record, **allowed)

    def _update_record(
        self,
        record: _JobRecord,
        *,
        status: JobStatus | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        **progress: object,
    ) -> None:
        if status is not None:
            record.status = status
        for key, value in progress.items():
            if key in JobProgress.model_fields:
                setattr(record.progress, key, value)
        record.error_code = error_code
        record.error_message = error_message
        record.updated_at = _now()
        record.version += 1

