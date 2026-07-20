import createClient, { type Middleware } from "openapi-fetch";

import { getBackendConnection, isDesktopApp } from "./desktop";
import type { components, paths } from "./generated/api-schema";
import i18n from "./i18n";

type Schemas = components["schemas"];

export type AuthConfig =
  | Schemas["GuestAuth-Input"]
  | Schemas["BrowserAuth-Input"]
  | Schemas["CookieSessionAuth-Input"];
export type AuthStatus = Schemas["AuthStatus"];
export type AutoAuthResult = Schemas["AutoAuthResult"];
export type QualityOption = Schemas["QualityOption"];
export type VideoPage = Schemas["VideoPage"];
export type ResolvedVideo = Schemas["ResolvedVideo"];
export type ResolvedResource = Schemas["ResolvedResource"];
export type ResourceItem = Schemas["ResourceItem"];
export type MediaKind = Schemas["MediaKind"];
export type AppStatus = Schemas["AppStatus"];
export type JobStatus = Schemas["JobStatus"];
export type CreateJobRequest = Schemas["CreateJobRequest-Input"];
export type JobView = Schemas["JobView"];
export type CookieSessionResult = Schemas["CookieSessionResult"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function extractError(payload: unknown, fallback: string): string {
  if (!isRecord(payload) || !("detail" in payload)) return fallback;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (isRecord(detail) && typeof detail.message === "string") return detail.message;
  if (Array.isArray(detail)) {
    const first = detail.find(
      (item): item is Record<string, unknown> => isRecord(item) && typeof item.msg === "string",
    );
    if (first && typeof first.msg === "string") return first.msg;
  }
  return fallback;
}

function requireData<T>(
  data: T | undefined,
  error: unknown,
  response: Response,
): T {
  if (data !== undefined) return data;
  throw new Error(extractError(error, i18n.t("errors.request", { status: response.status })));
}

function requireSuccess(error: unknown, response: Response): void {
  if (response.ok) return;
  throw new Error(extractError(error, i18n.t("errors.request", { status: response.status })));
}

const JOB_STATUSES = new Set<JobStatus>([
  "queued",
  "running",
  "completed",
  "partial",
  "failed",
  "cancelled",
]);

function parseJobView(value: unknown): JobView {
  if (
    !isRecord(value)
    || typeof value.id !== "string"
    || typeof value.status !== "string"
    || !JOB_STATUSES.has(value.status as JobStatus)
    || !isRecord(value.request)
    || !isRecord(value.progress)
    || !Array.isArray(value.result_paths)
    || typeof value.created_at !== "string"
    || typeof value.updated_at !== "string"
  ) {
    throw new Error(i18n.t("errors.invalidJob"));
  }
  return value as JobView;
}

export class ApiClient {
  private readonly connection: ReturnType<typeof getBackendConnection>;
  private readonly client: Promise<ReturnType<typeof createClient<paths>>>;

  constructor(token: string) {
    this.connection = getBackendConnection(token);
    this.client = this.connection.then((connection) => {
      const client = createClient<paths>({ baseUrl: connection.base_url });
      const tokenMiddleware: Middleware = {
        onRequest: ({ request }) => {
          request.headers.set("X-Bilidown-Token", connection.token);
          return request;
        },
      };
      client.use(tokenMiddleware);
      return client;
    });
  }

  async getStatus(): Promise<AppStatus> {
    const client = await this.client;
    const { data, error, response } = await client.GET("/api/status");
    return requireData(data, error, response);
  }

  async resolve(credential: string, auth: AuthConfig): Promise<ResolvedVideo> {
    const client = await this.client;
    const { data, error, response } = await client.POST("/api/resolve", {
      body: { credential, auth },
    });
    return requireData(data, error, response);
  }

  async resolveResource(
    credential: string,
    auth: AuthConfig,
  ): Promise<ResolvedResource> {
    const client = await this.client;
    const { data, error, response } = await client.POST(
      "/api/resources/resolve",
      { body: { credential, auth } },
    );
    return requireData(data, error, response);
  }

  async checkAuth(auth: AuthConfig): Promise<AuthStatus> {
    const client = await this.client;
    const { data, error, response } = await client.POST("/api/auth/status", {
      body: { auth },
    });
    return requireData(data, error, response);
  }

  async autoSelectAuth(): Promise<AutoAuthResult> {
    const client = await this.client;
    const { data, error, response } = await client.POST("/api/auth/auto");
    return requireData(data, error, response);
  }

  async uploadCookies(file: File): Promise<CookieSessionResult> {
    const connection = await this.connection;
    const body = new FormData();
    body.set("file", file);
    const response = await fetch(`${connection.base_url}/api/auth/cookie-sessions`, {
      method: "POST",
      headers: { "X-Bilidown-Token": connection.token },
      body,
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(extractError(payload, i18n.t("errors.request", { status: response.status })));
    }
    if (
      !isRecord(payload)
      || typeof payload.session_id !== "string"
      || typeof payload.cookie_count !== "number"
    ) {
      throw new Error(i18n.t("errors.invalidCookieSession"));
    }
    return {
      session_id: payload.session_id,
      cookie_count: payload.cookie_count,
    };
  }

  async deleteCookieSession(sessionId: string): Promise<void> {
    const client = await this.client;
    const { error, response } = await client.DELETE(
      "/api/auth/cookie-sessions/{session_id}",
      { params: { path: { session_id: sessionId } } },
    );
    requireSuccess(error, response);
  }

  async listJobs(): Promise<JobView[]> {
    const client = await this.client;
    const { data, error, response } = await client.GET("/api/jobs");
    return requireData(data, error, response);
  }

  async createJob(request: CreateJobRequest): Promise<JobView> {
    const client = await this.client;
    const { data, error, response } = await client.POST("/api/jobs", {
      body: request,
    });
    return requireData(data, error, response);
  }

  async cancelJob(jobId: string): Promise<JobView> {
    const client = await this.client;
    const { data, error, response } = await client.POST(
      "/api/jobs/{job_id}/cancel",
      { params: { path: { job_id: jobId } } },
    );
    return requireData(data, error, response);
  }

  async retryJob(jobId: string): Promise<JobView> {
    const client = await this.client;
    const { data, error, response } = await client.POST(
      "/api/jobs/{job_id}/retry",
      { params: { path: { job_id: jobId } } },
    );
    return requireData(data, error, response);
  }

  async openOutput(path: string): Promise<void> {
    const client = await this.client;
    const { error, response } = await client.POST("/api/open-output", {
      body: { path },
    });
    requireSuccess(error, response);
  }

  async quit(): Promise<void> {
    const client = await this.client;
    const { error, response } = await client.POST("/api/quit");
    requireSuccess(error, response);
  }

  async streamJob(jobId: string, onUpdate: (job: JobView) => void): Promise<void> {
    const connection = await this.connection;
    const response = await fetch(`${connection.base_url}/api/jobs/${encodeURIComponent(jobId)}/events`, {
      headers: { "X-Bilidown-Token": connection.token },
    });
    if (!response.ok || !response.body) throw new Error(i18n.t("errors.subscribe"));
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
        if (data) onUpdate(parseJobView(JSON.parse(data) as unknown));
      }
      if (done) return;
    }
  }
}

export function readSessionToken(): string {
  if (isDesktopApp()) return "desktop-session";
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
