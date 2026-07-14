import type { ResolvedVideo } from "../api";

interface VideoPreviewProps {
  video: ResolvedVideo;
  selectedPages: Set<number>;
  onSelectedPagesChange: (pages: Set<number>) => void;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return "时长未知";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = Math.floor(seconds % 60);
  return [hours, minutes, remaining]
    .filter((_, index) => hours > 0 || index > 0)
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function VideoPreview({ video, selectedPages, onSelectedPagesChange }: VideoPreviewProps) {
  function togglePage(index: number) {
    const next = new Set(selectedPages);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    onSelectedPagesChange(next);
  }

  const allSelected = selectedPages.size === video.pages.length;

  return (
    <section className="panel video-preview" aria-labelledby="video-heading">
      <div className="cover-frame">
        {video.thumbnail ? <img src={video.thumbnail} alt={`${video.title} 封面`} /> : <div className="cover-placeholder">NO COVER</div>}
      </div>
      <div className="video-details">
        <p className="eyebrow">解析完成 · {video.bvid}</p>
        <h2 id="video-heading">{video.title}</h2>
        <p className="video-meta">{video.uploader ?? "未知 UP 主"} · {formatDuration(video.duration)} · {video.pages.length} P</p>

        <div className="page-toolbar">
          <h3>选择分 P</h3>
          <button
            type="button"
            className="text-button"
            onClick={() => onSelectedPagesChange(allSelected ? new Set() : new Set(video.pages.map((page) => page.index)))}
          >
            {allSelected ? "取消全选" : "选择全部"}
          </button>
        </div>
        <div className="page-list">
          {video.pages.map((page) => (
            <label className="page-option" key={page.index}>
              <input type="checkbox" checked={selectedPages.has(page.index)} onChange={() => togglePage(page.index)} />
              <span className="page-number">P{String(page.index).padStart(2, "0")}</span>
              <span className="page-title">{page.title}</span>
              <span className="page-duration">{formatDuration(page.duration)}</span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}

