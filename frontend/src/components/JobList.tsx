import type { JobView } from "../api";

interface JobListProps {
  jobs: JobView[];
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
}

const STATUS_LABELS: Record<JobView["status"], string> = {
  queued: "排队中",
  running: "进行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

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
  return (
    <section className="panel jobs-panel" aria-labelledby="jobs-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">本次运行</p>
          <h2 id="jobs-heading">任务队列</h2>
        </div>
        <span>{jobs.length} 个任务</span>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">创建下载任务后，进度会显示在这里。</div>
      ) : (
        <div className="job-list">
          {jobs.map((job) => (
            <article className="job-item" key={job.id}>
              <div className="job-main">
                <span className={`job-status ${job.status}`}>{STATUS_LABELS[job.status]}</span>
                <div>
                  <h3>
                    {job.request.media_kind === "cover"
                      ? "原始封面"
                      : job.request.media_kind === "audio"
                        ? "音频"
                        : job.request.quality_height
                          ? `${job.request.quality_height}P 视频`
                          : "视频"}
                  </h3>
                  <p>{job.progress.phase}{job.progress.current_page ? ` · P${job.progress.current_page}` : ""}</p>
                </div>
              </div>
              <progress max={100} value={job.progress.percent ?? 0}>{job.progress.percent ?? 0}%</progress>
              <div className="job-metrics">
                <span>{job.progress.percent?.toFixed(1) ?? "0.0"}%</span>
                <span>{formatBytes(job.progress.downloaded_bytes)} / {formatBytes(job.progress.total_bytes)}</span>
                <span>{job.progress.speed ? `${formatBytes(job.progress.speed)}/s` : "等待速度"}</span>
              </div>
              {job.error_message && <details className="job-error"><summary>查看错误</summary><p>{job.error_message}</p></details>}
              {job.result_paths.length > 0 && <p className="result-path">{job.result_paths.join("\n")}</p>}
              <div className="job-actions">
                {(job.status === "queued" || job.status === "running") && (
                  <button type="button" className="danger-button" onClick={() => onCancel(job.id)}>取消</button>
                )}
                {(job.status === "failed" || job.status === "cancelled") && (
                  <button type="button" className="secondary-button" onClick={() => onRetry(job.id)}>重试</button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
