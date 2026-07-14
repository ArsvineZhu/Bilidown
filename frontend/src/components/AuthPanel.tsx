import { useState } from "react";

import type { ApiClient, AuthConfig, AuthStatus } from "../api";

interface AuthPanelProps {
  api: ApiClient;
  auth: AuthConfig;
  authStatus: AuthStatus | null;
  checking: boolean;
  checkError: string | null;
  onRefresh: () => void;
  onChange: (auth: AuthConfig) => void;
  disabled?: boolean;
}

export function AuthPanel({
  api,
  auth,
  authStatus,
  checking,
  checkError,
  onRefresh,
  onChange,
  disabled = false,
}: AuthPanelProps) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleCookieFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      const session = await api.uploadCookies(file);
      onChange({ kind: "cookie_session", session_id: session.session_id });
      setMessage(`已载入 ${session.cookie_count} 条 Bilibili Cookie，本次运行有效。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Cookie 文件读取失败");
    } finally {
      setUploading(false);
    }
  }

  const sourceLabel = auth.kind === "guest"
    ? "游客"
    : auth.kind === "browser"
      ? auth.browser[0].toUpperCase() + auth.browser.slice(1)
      : "cookies.txt";
  const statusTone = checking
    ? "checking"
    : checkError
      ? "error"
      : authStatus?.state === "active"
        ? "active"
        : authStatus?.state === "inactive"
          ? "inactive"
          : "guest";
  const statusText = checking
    ? "正在检查登录状态…"
    : checkError
      ? checkError
      : authStatus?.state === "active"
        ? `${authStatus.username ?? "已登录账号"} · ${authStatus.vip_active ? authStatus.vip_label ?? "大会员" : "普通账号"}`
        : authStatus?.state === "inactive"
          ? "未检测到有效登录态"
          : "未使用账号权限";

  return (
    <section className="panel auth-panel" aria-labelledby="auth-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">登录权限</p>
          <h2 id="auth-heading">选择登录来源</h2>
        </div>
        <span className="privacy-badge">仅本机处理</span>
      </div>

      <div className="segmented" role="group" aria-label="登录来源">
        <button
          type="button"
          className={auth.kind === "guest" ? "active" : ""}
          onClick={() => onChange({ kind: "guest" })}
          disabled={disabled}
        >
          游客
        </button>
        {(["chrome", "edge", "firefox"] as const).map((browser) => (
          <button
            type="button"
            className={auth.kind === "browser" && auth.browser === browser ? "active" : ""}
            onClick={() => onChange({ kind: "browser", browser })}
            disabled={disabled}
            key={browser}
          >
            {browser[0].toUpperCase() + browser.slice(1)}
          </button>
        ))}
      </div>

      {auth.kind === "browser" && (
        <label className="field compact-field">
          <span>浏览器 Profile（可选）</span>
          <input
            value={auth.profile ?? ""}
            onChange={(event) =>
              onChange({ kind: "browser", browser: auth.browser, profile: event.target.value || undefined })
            }
            placeholder="留空使用最近访问的 Profile"
            disabled={disabled}
          />
        </label>
      )}

      <div className="cookie-row">
        <label className="file-button">
          <input
            type="file"
            accept=".txt,text/plain"
            onChange={(event) => void handleCookieFile(event.target.files?.[0])}
            disabled={disabled || uploading}
          />
          {uploading ? "正在读取…" : "载入 cookies.txt"}
        </label>
        <span>{auth.kind === "cookie_session" ? "Cookie 文件登录已启用" : "也可使用 Netscape Cookie 文件"}</span>
      </div>
      {message && <p className="inline-message" role="status">{message}</p>}
      <div className={`auth-status-card ${statusTone}`} aria-live="polite">
        <span className="auth-status-indicator" aria-hidden="true" />
        <div>
          <strong>{sourceLabel}</strong>
          <p>{statusText}</p>
        </div>
        <button
          type="button"
          className="secondary-button auth-refresh"
          onClick={onRefresh}
          disabled={disabled || checking}
        >
          重新检查
        </button>
      </div>
    </section>
  );
}
