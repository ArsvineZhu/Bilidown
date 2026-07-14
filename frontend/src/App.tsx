import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiClient, readSessionToken } from "./api";
import type { AppStatus, AuthConfig, AuthStatus, CreateJobRequest, JobView, QualityOption, ResolvedVideo } from "./api";
import { AuthPanel } from "./components/AuthPanel";
import { DownloadPanel } from "./components/DownloadPanel";
import { JobList } from "./components/JobList";
import { VideoPreview } from "./components/VideoPreview";

const token = readSessionToken();
const api = new ApiClient(token);
const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

function updateJobList(jobs: JobView[], updated: JobView): JobView[] {
  const index = jobs.findIndex((job) => job.id === updated.id);
  if (index === -1) return [updated, ...jobs];
  return jobs.map((job) => (job.id === updated.id ? updated : job));
}

export function App() {
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [auth, setAuth] = useState<AuthConfig>({ kind: "guest" });
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [authChecking, setAuthChecking] = useState(false);
  const [authCheckError, setAuthCheckError] = useState<string | null>(null);
  const [authCheckNonce, setAuthCheckNonce] = useState(0);
  const [credential, setCredential] = useState("");
  const [video, setVideo] = useState<ResolvedVideo | null>(null);
  const [selectedPages, setSelectedPages] = useState<Set<number>>(new Set());
  const [qualityId, setQualityId] = useState<string | null>(null);
  const [videoMode, setVideoMode] = useState<"compatible_mp4" | "source_auto">("compatible_mp4");
  const [audioFormat, setAudioFormat] = useState<"best_source" | "m4a" | "mp3">("m4a");
  const [outputDir, setOutputDir] = useState("");
  const [jobs, setJobs] = useState<JobView[]>([]);
  const [resolving, setResolving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchedJobs = useRef(new Set<string>());

  const watchJob = useCallback((job: JobView) => {
    if (TERMINAL_STATUSES.has(job.status) || watchedJobs.current.has(job.id)) return;
    watchedJobs.current.add(job.id);
    void api
      .streamJob(job.id, (updated) => setJobs((current) => updateJobList(current, updated)))
      .catch((streamError: unknown) => {
        setError(streamError instanceof Error ? streamError.message : "任务进度连接中断");
      })
      .finally(() => watchedJobs.current.delete(job.id));
  }, []);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    Promise.all([api.getStatus(), api.listJobs()])
      .then(([nextStatus, nextJobs]) => {
        if (controller.signal.aborted) return;
        setStatus(nextStatus);
        setOutputDir(nextStatus.default_output_dir);
        setJobs(nextJobs);
        nextJobs.forEach(watchJob);
      })
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) setError(loadError instanceof Error ? loadError.message : "应用初始化失败");
      });
    return () => controller.abort();
  }, [watchJob]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setAuthChecking(true);
    setAuthCheckError(null);
    const timer = window.setTimeout(
      () => {
        void api
          .checkAuth(auth)
          .then((nextStatus) => {
            if (!cancelled) setAuthStatus(nextStatus);
          })
          .catch((checkError: unknown) => {
            if (!cancelled) {
              setAuthStatus(null);
              setAuthCheckError(checkError instanceof Error ? checkError.message : "登录状态检查失败");
            }
          })
          .finally(() => {
            if (!cancelled) setAuthChecking(false);
          });
      },
      auth.kind === "browser" && auth.profile ? 450 : 0,
    );
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [auth, authCheckNonce]);

  function handleAuthChange(nextAuth: AuthConfig) {
    if (
      auth.kind === "cookie_session" &&
      (nextAuth.kind !== "cookie_session" || nextAuth.session_id !== auth.session_id)
    ) {
      void api.deleteCookieSession(auth.session_id).catch(() => undefined);
    }
    setAuth(nextAuth);
  }

  const commonQualities = useMemo<QualityOption[]>(() => {
    if (!video || selectedPages.size === 0) return [];
    const pages = video.pages.filter((page) => selectedPages.has(page.index));
    const commonIds = new Set(pages[0]?.qualities.map((quality) => quality.id) ?? []);
    for (const page of pages.slice(1)) {
      const ids = new Set(page.qualities.map((quality) => quality.id));
      for (const id of commonIds) if (!ids.has(id)) commonIds.delete(id);
    }
    return (pages[0]?.qualities ?? []).filter(
      (quality) => commonIds.has(quality.id) && (videoMode === "source_auto" || quality.compatibility === "preferred"),
    );
  }, [selectedPages, video, videoMode]);

  useEffect(() => {
    if (!commonQualities.some((quality) => quality.id === qualityId)) {
      setQualityId(commonQualities[0]?.id ?? null);
    }
  }, [commonQualities, qualityId]);

  async function handleResolve(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResolving(true);
    setError(null);
    try {
      const resolved = await api.resolve(credential, auth);
      setVideo(resolved);
      setCredential(resolved.canonical_url);
      setSelectedPages(new Set([resolved.selected_page]));
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : "视频解析失败");
    } finally {
      setResolving(false);
    }
  }

  async function handleCreate(kind: "cover" | "audio" | "video") {
    if (!video || !status) return;
    setCreating(true);
    setError(null);
    const selectedQuality = commonQualities.find((quality) => quality.id === qualityId);
    const request: CreateJobRequest = {
      credential: video.canonical_url,
      media_kind: kind,
      page_indices: kind === "cover" ? [] : [...selectedPages].sort((a, b) => a - b),
      quality_height: kind === "video" ? selectedQuality?.height : undefined,
      quality_id: kind === "video" ? qualityId ?? undefined : undefined,
      video_mode: videoMode,
      audio_format: audioFormat,
      auth,
      output_dir: outputDir,
    };
    try {
      const job = await api.createJob(request);
      setJobs((current) => updateJobList(current, job));
      watchJob(job);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "无法创建下载任务");
    } finally {
      setCreating(false);
    }
  }

  async function handleCancel(jobId: string) {
    try {
      const job = await api.cancelJob(jobId);
      setJobs((current) => updateJobList(current, job));
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "取消任务失败");
    }
  }

  async function handleRetry(jobId: string) {
    try {
      const job = await api.retryJob(jobId);
      setJobs((current) => updateJobList(current, job));
      watchJob(job);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "重试任务失败");
    }
  }

  if (!token) {
    return <main className="fatal-state"><h1>本地会话已失效</h1><p>请关闭此页面并重新启动 Bilidown。</p></main>;
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-mark">B</div>
        <div>
          <p className="eyebrow">LOCAL MEDIA TOOL</p>
          <h1>Bilidown</h1>
        </div>
        <div className="header-status">
          <span>仅监听 127.0.0.1</span>
          {status && <span>v{status.app_version} · yt-dlp {status.yt_dlp_version}</span>}
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">BILIBILI UGC DOWNLOADER</p>
          <h2>把你有权保存的内容，<br /><em>留在本机。</em></h2>
          <p>输入 BV 号、AV 号、视频链接或 b23.tv 短链。登录态、解析过程和下载记录不会发送给第三方。</p>
        </div>
        <div className="hero-number">01—03</div>
      </section>

      <AuthPanel
        api={api}
        auth={auth}
        authStatus={authStatus}
        checking={authChecking}
        checkError={authCheckError}
        onRefresh={() => setAuthCheckNonce((value) => value + 1)}
        onChange={handleAuthChange}
        disabled={resolving}
      />

      <section className="panel resolver-panel" aria-labelledby="resolver-heading">
        <p className="eyebrow">视频定位</p>
        <h2 id="resolver-heading">粘贴凭据并解析</h2>
        <form className="resolver-form" onSubmit={handleResolve}>
          <label className="sr-only" htmlFor="credential">BV 号、AV 号或视频链接</label>
          <input
            id="credential"
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
            placeholder="BV1xx411c7mD 或 https://www.bilibili.com/video/..."
            disabled={resolving}
            required
          />
          <button type="submit" disabled={resolving}>{resolving ? "解析中…" : "解析视频"}</button>
        </form>
        {error && <div className="error-banner" role="alert">{error}</div>}
      </section>

      {video && <VideoPreview video={video} selectedPages={selectedPages} onSelectedPagesChange={setSelectedPages} />}
      {video && status && (
        <DownloadPanel
          status={status}
          outputDir={outputDir}
          onOutputDirChange={setOutputDir}
          qualities={commonQualities}
          qualityId={qualityId}
          onQualityIdChange={setQualityId}
          videoMode={videoMode}
          onVideoModeChange={setVideoMode}
          audioFormat={audioFormat}
          onAudioFormatChange={setAudioFormat}
          selectedPageCount={selectedPages.size}
          busy={creating}
          onCreate={(kind) => void handleCreate(kind)}
          onOpenOutput={() => void api.openOutput(outputDir).catch((openError: unknown) => setError(openError instanceof Error ? openError.message : "无法打开目录"))}
        />
      )}
      <JobList jobs={jobs} onCancel={(id) => void handleCancel(id)} onRetry={(id) => void handleRetry(id)} />

      <footer>
        <p>Bilidown 不绕过权限。请遵守 Bilibili 条款及适用版权法律。</p>
        {status && <p>FFmpeg {status.ffmpeg_version ?? "未安装"}</p>}
      </footer>
    </main>
  );
}
