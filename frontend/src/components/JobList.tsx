import { useTranslation } from "react-i18next";

import type { JobView } from "../api";

interface JobListProps {
  jobs: JobView[];
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
}

function formatBytes(value: number | null): string {
  if (!value) return "—";
  const units = ["B", "KiB", "MiB", "GiB"];
  let number = value;
  let index = 0;
  while (number >= 1024 && index < units.length - 1) {
    number /= 1024;
    index += 1;
  }
  return `${number.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function JobList({ jobs, onCancel, onRetry }: JobListProps) {
  const { t } = useTranslation();
  const statusLabels: Record<JobView["status"], string> = {
    queued: t("jobs.queued"),
    running: t("jobs.running"),
    completed: t("jobs.completed"),
    partial: t("jobs.partial"),
    failed: t("jobs.failed"),
    cancelled: t("jobs.cancelled"),
  };
  return (
    <section className="panel jobs-panel" aria-labelledby="jobs-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("jobs.eyebrow")}</p>
          <h2 id="jobs-heading">{t("jobs.title")}</h2>
        </div>
        <span>{t("jobs.count", { count: jobs.length })}</span>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">{t("jobs.empty")}</div>
      ) : (
        <div className="job-list">
          {jobs.map((job) => (
            <article className="job-item" key={job.id}>
              <div className="job-main">
                <span className={`job-status ${job.status}`}>{statusLabels[job.status]}</span>
                <div>
                  <h3>
                    {job.request.media_kind === "cover"
                      ? t("jobs.cover")
                      : job.request.media_kind === "audio"
                        ? t("jobs.audio")
                        : job.request.media_kind === "subtitles"
                          ? t("jobs.subtitles")
                          : job.request.media_kind === "danmaku_xml"
                            ? t("jobs.danmakuXml")
                            : job.request.media_kind === "danmaku_ass"
                              ? t("jobs.danmakuAss")
                        : job.request.quality_height
                          ? t("jobs.qualityVideo", { height: job.request.quality_height })
                          : t("jobs.video")}
                  </h3>
                  <p>{job.progress.phase}{job.progress.current_page ? ` · P${job.progress.current_page}` : ""}</p>
                </div>
              </div>
              <progress max={100} value={job.progress.percent ?? 0}>{job.progress.percent ?? 0}%</progress>
              <div className="job-metrics">
                <span>{job.progress.percent?.toFixed(1) ?? "0.0"}%</span>
                <span>{formatBytes(job.progress.downloaded_bytes)} / {formatBytes(job.progress.total_bytes)}</span>
                <span>{job.progress.speed ? `${formatBytes(job.progress.speed)}/s` : t("jobs.waitingSpeed")}</span>
              </div>
              {job.error_message && <details className="job-error"><summary>{t("jobs.showError")}</summary><p>{job.error_message}</p></details>}
              {job.item_results.some((item) => item.status === "failed") && (
                <details className="job-error">
                  <summary>
                    {t("jobs.failedItems", {
                      count: job.item_results.filter((item) => item.status === "failed").length,
                    })}
                  </summary>
                  {job.item_results
                    .filter((item) => item.status === "failed")
                    .map((item) => (
                      <p key={item.url}>{item.url}: {item.error_message ?? t("jobs.failed")}</p>
                    ))}
                </details>
              )}
              {job.result_paths.length > 0 && <p className="result-path">{job.result_paths.join("\n")}</p>}
              <div className="job-actions">
                {(job.status === "queued" || job.status === "running") && (
                  <button type="button" className="danger-button" onClick={() => onCancel(job.id)}>{t("jobs.cancel")}</button>
                )}
                {(job.status === "partial" || job.status === "failed" || job.status === "cancelled") && (
                  <button type="button" className="secondary-button" onClick={() => onRetry(job.id)}>{t("jobs.retry")}</button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
