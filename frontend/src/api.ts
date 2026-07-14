export type AuthConfig =
  | { kind: "guest" }
  | { kind: "browser"; browser: "chrome" | "edge" | "firefox"; profile?: string }
  | { kind: "cookie_session"; session_id: string };

export interface AuthStatus {
  state: "guest" | "active" | "inactive";
  username: string | null;
  vip_active: boolean;
  vip_label: string | null;
}

export interface QualityOption {
  id: string;
  label: string;
  height: number;
  width: number | null;
  fps: number | null;
  quality_code: number | null;
  format_name: string;
  bitrate_kbps: number | null;
  dynamic_range: string | null;
  codec_family: "H.264" | "HEVC" | "AV1" | "Other";
  video_codec: string;
  audio_codec: string | null;
  container: string;
  compatibility: "preferred" | "fallback";
}

export interface VideoPage {
  index: number;
  cid: number | null;
  title: string;
  duration: number | null;
  qualities: QualityOption[];
}

export interface ResolvedVideo {
  canonical_url: string;
  bvid: string;
  aid: number | null;
  title: string;
  uploader: string | null;
  thumbnail: string | null;
  duration: number | null;
  selected_page: number;
  pages: VideoPage[];
}

export interface AppStatus {
  app_version: string;
  yt_dlp_version: string;
  ffmpeg_version: string | null;
  ffmpeg_available: boolean;
  default_output_dir: string;
}

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface CreateJobRequest {
  credential: string;
  media_kind: "cover" | "audio" | "video";
  page_indices: number[];
  quality_height?: number;
  quality_id?: string;
  video_mode: "compatible_mp4" | "source_auto";
  audio_format: "original" | "best_source" | "m4a" | "mp3";
  auth: AuthConfig;
  output_dir: string;
}

export interface JobView {
  id: string;
  status: JobStatus;
  request: CreateJobRequest;
  progress: {
    phase: string;
    current_page: number | null;
    downloaded_bytes: number | null;
    total_bytes: number | null;
    percent: number | null;
    speed: number | null;
    eta: number | null;
  };
  result_paths: string[];
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

function extractError(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return fallback;
  }
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return fallback;
}

export class ApiClient {
  constructor(private readonly token: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("X-Bilidown-Token", this.token);
    if (init.body && !(init.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    const response = await fetch(path, { ...init, headers });
    if (!response.ok) {
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new Error(extractError(payload, `请求失败 (${response.status})`));
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  getStatus(): Promise<AppStatus> {
    return this.request("/api/status");
  }

  resolve(credential: string, auth: AuthConfig): Promise<ResolvedVideo> {
    return this.request("/api/resolve", {
      method: "POST",
      body: JSON.stringify({ credential, auth }),
    });
  }

  checkAuth(auth: AuthConfig): Promise<AuthStatus> {
    return this.request("/api/auth/status", {
      method: "POST",
      body: JSON.stringify({ auth }),
    });
  }

  async uploadCookies(file: File): Promise<{ session_id: string; cookie_count: number }> {
    const body = new FormData();
    body.set("file", file);
    return this.request("/api/auth/cookie-sessions", { method: "POST", body });
  }

  deleteCookieSession(sessionId: string): Promise<void> {
    return this.request(`/api/auth/cookie-sessions/${sessionId}`, { method: "DELETE" });
  }

  listJobs(): Promise<JobView[]> {
    return this.request("/api/jobs");
  }

  createJob(request: CreateJobRequest): Promise<JobView> {
    return this.request("/api/jobs", { method: "POST", body: JSON.stringify(request) });
  }

  cancelJob(jobId: string): Promise<JobView> {
    return this.request(`/api/jobs/${jobId}/cancel`, { method: "POST" });
  }

  retryJob(jobId: string): Promise<JobView> {
    return this.request(`/api/jobs/${jobId}/retry`, { method: "POST" });
  }

  openOutput(path: string): Promise<void> {
    return this.request("/api/open-output", { method: "POST", body: JSON.stringify({ path }) });
  }

  async streamJob(jobId: string, onUpdate: (job: JobView) => void): Promise<void> {
    const response = await fetch(`/api/jobs/${jobId}/events`, {
      headers: { "X-Bilidown-Token": this.token },
    });
    if (!response.ok || !response.body) throw new Error("无法订阅任务进度");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const messages = buffer.split("\n\n");
      buffer = messages.pop() ?? "";
      for (const message of messages) {
        const data = message
          .split("\n")
          .find((line) => line.startsWith("data: "))
          ?.slice(6);
        if (data) onUpdate(JSON.parse(data) as JobView);
      }
      if (done) return;
    }
  }
}

export function readSessionToken(): string {
  const url = new URL(window.location.href);
  const fromUrl = url.searchParams.get("token");
  if (fromUrl) {
    sessionStorage.setItem("bilidown-token", fromUrl);
    url.searchParams.delete("token");
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    return fromUrl;
  }
  return sessionStorage.getItem("bilidown-token") ?? "";
}
