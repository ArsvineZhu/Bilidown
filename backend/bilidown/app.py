from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import httpx
import yt_dlp.version
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .cookies import CookieStore, InvalidCookieFile
from .engine import DownloaderEngine, EngineError
from .files import ensure_output_directory
from .input_parser import InvalidCredential, normalize_credential
from .jobs import JobManager
from .models import (
    AppStatus,
    AuthStatus,
    AuthStatusRequest,
    CreateJobRequest,
    JobStatus,
    JobView,
    OpenOutputRequest,
    ResolveRequest,
    ResolvedVideo,
)
from .runtime import ffmpeg_version, find_ffmpeg_binary, frontend_dist
from .security import LocalSecurityMiddleware


def default_output_directory() -> Path:
    return Path.home() / "Downloads" / "Bilidown"


def open_output_directory(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(
            ["open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    raise NotImplementedError("当前平台暂不支持打开目录")


def create_app(*, session_token: str, expected_origin: str, static_dir: Path | None = None) -> FastAPI:
    cookies = CookieStore()
    engine = DownloaderEngine(cookies)
    jobs = JobManager(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await jobs.start()
        try:
            yield
        finally:
            await jobs.stop()
            cookies.clear()

    app = FastAPI(title="Bilidown", version=__version__, lifespan=lifespan)
    app.state.cookie_store = cookies
    app.state.engine = engine
    app.state.jobs = jobs
    app.add_middleware(
        LocalSecurityMiddleware,
        token=session_token,
        expected_origin=expected_origin,
    )

    @app.get("/api/status", response_model=AppStatus)
    async def status() -> AppStatus:
        version = ffmpeg_version()
        return AppStatus(
            app_version=__version__,
            yt_dlp_version=yt_dlp.version.__version__,
            ffmpeg_version=version,
            ffmpeg_available=find_ffmpeg_binary("ffmpeg") is not None
            and find_ffmpeg_binary("ffprobe") is not None,
            default_output_dir=str(default_output_directory()),
        )

    @app.post("/api/resolve", response_model=ResolvedVideo)
    async def resolve(request: ResolveRequest) -> ResolvedVideo:
        try:
            normalized = await normalize_credential(request.credential)
            return await asyncio.to_thread(engine.resolve, normalized, request.auth)
        except InvalidCredential as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except InvalidCookieFile as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

    @app.post("/api/auth/status", response_model=AuthStatus)
    async def auth_status(request: AuthStatusRequest) -> AuthStatus:
        try:
            return await asyncio.to_thread(engine.auth_status, request.auth)
        except InvalidCookieFile as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EngineError as exc:
            status_code = 502 if exc.code == "auth_status_unavailable" else 400
            raise HTTPException(
                status_code=status_code,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

    @app.post("/api/auth/cookie-sessions")
    async def create_cookie_session(file: UploadFile = File(...)) -> dict[str, object]:
        payload = await file.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="Cookie 文件不能超过 1 MiB")
        try:
            content = payload.decode("utf-8-sig")
            session = cookies.create(content)
        except (UnicodeDecodeError, InvalidCookieFile) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session_id": session.id, "cookie_count": session.cookie_count}

    @app.delete(
        "/api/auth/cookie-sessions/{session_id}",
        status_code=204,
        response_class=Response,
        response_model=None,
    )
    async def delete_cookie_session(session_id: str) -> Response:
        if not cookies.delete(session_id):
            raise HTTPException(status_code=404, detail="Cookie 会话不存在")
        return Response(status_code=204)

    @app.get("/api/jobs", response_model=list[JobView])
    async def list_jobs() -> list[JobView]:
        return jobs.list()

    @app.post("/api/jobs", response_model=JobView, status_code=201)
    async def create_job(request: CreateJobRequest) -> JobView:
        if request.media_kind != "cover" and find_ffmpeg_binary("ffmpeg") is None:
            raise HTTPException(status_code=409, detail="未找到 ffmpeg，无法创建媒体任务")
        try:
            ensure_output_directory(request.output_dir)
            return await jobs.submit(request)
        except (InvalidCredential, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/jobs/{job_id}", response_model=JobView)
    async def get_job(job_id: str) -> JobView:
        try:
            return jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="任务不存在") from exc

    @app.post("/api/jobs/{job_id}/cancel", response_model=JobView)
    async def cancel_job(job_id: str) -> JobView:
        try:
            return jobs.cancel(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="任务不存在") from exc

    @app.post("/api/jobs/{job_id}/retry", response_model=JobView, status_code=201)
    async def retry_job(job_id: str) -> JobView:
        try:
            return await jobs.retry(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="任务不存在") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str) -> StreamingResponse:
        try:
            jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="任务不存在") from exc

        async def stream() -> AsyncIterator[str]:
            version = -1
            while True:
                try:
                    view = jobs.get(job_id)
                    current = jobs.get_version(job_id)
                except KeyError:
                    return
                if current != version:
                    version = current
                    payload = json.dumps(view.model_dump(mode="json"), ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                if view.status in {
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                }:
                    return
                await asyncio.sleep(0.35)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post(
        "/api/open-output",
        status_code=204,
        response_class=Response,
        response_model=None,
    )
    async def open_output(request: OpenOutputRequest) -> Response:
        try:
            path = ensure_output_directory(request.path)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            open_output_directory(path)
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail="无法调用系统文件管理器") from exc
        return Response(status_code=204)

    resolved_static = static_dir if static_dir is not None else frontend_dist()
    if resolved_static.is_dir() and (resolved_static / "index.html").is_file():
        app.mount("/", StaticFiles(directory=resolved_static, html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def missing_frontend() -> str:
            return "<h1>Bilidown</h1><p>Frontend assets are not built.</p>"

    return app
