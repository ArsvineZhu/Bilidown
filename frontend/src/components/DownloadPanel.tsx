import type { AppStatus, QualityOption } from "../api";

interface DownloadPanelProps {
  status: AppStatus;
  outputDir: string;
  onOutputDirChange: (value: string) => void;
  qualities: QualityOption[];
  qualityId: string | null;
  onQualityIdChange: (value: string) => void;
  videoMode: "compatible_mp4" | "source_auto";
  onVideoModeChange: (value: "compatible_mp4" | "source_auto") => void;
  audioFormat: "best_source" | "m4a" | "mp3";
  onAudioFormatChange: (value: "best_source" | "m4a" | "mp3") => void;
  selectedPageCount: number;
  busy: boolean;
  onCreate: (kind: "cover" | "audio" | "video") => void;
  onOpenOutput: () => void;
}

export function DownloadPanel({
  status,
  outputDir,
  onOutputDirChange,
  qualities,
  qualityId,
  onQualityIdChange,
  videoMode,
  onVideoModeChange,
  audioFormat,
  onAudioFormatChange,
  selectedPageCount,
  busy,
  onCreate,
  onOpenOutput,
}: DownloadPanelProps) {
  const selectedQuality = qualities.find((item) => item.id === qualityId);
  return (
    <section className="panel download-panel" aria-labelledby="download-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">下载配置</p>
          <h2 id="download-heading">选择要保存的内容</h2>
        </div>
        <span className={status.ffmpeg_available ? "status-dot good" : "status-dot warning"}>
          {status.ffmpeg_available ? "FFmpeg 就绪" : "缺少 FFmpeg"}
        </span>
      </div>

      <div className="download-grid">
        <article className="download-card accent-cover">
          <span className="card-index">01</span>
          <h3>原始封面</h3>
          <p>保存 Bilibili 返回的原始图片，不放大、不压缩。</p>
          <button type="button" onClick={() => onCreate("cover")} disabled={busy}>下载封面</button>
        </article>

        <article className="download-card accent-audio">
          <span className="card-index">02</span>
          <h3>音频</h3>
          <label className="field">
            <span>输出格式</span>
            <select value={audioFormat} onChange={(event) => onAudioFormatChange(event.target.value as "best_source" | "m4a" | "mp3")}>
              <option value="m4a">AAC / M4A 源流</option>
              <option value="best_source">最佳源流（FLAC / Dolby / AAC）</option>
              <option value="mp3">MP3 VBR V2</option>
            </select>
          </label>
          <button type="button" onClick={() => onCreate("audio")} disabled={busy || !status.ffmpeg_available || selectedPageCount === 0}>
            下载 {selectedPageCount} P 音频
          </button>
        </article>

        <article className="download-card accent-video">
          <span className="card-index">03</span>
          <h3>视频</h3>
          <label className="field">
            <span>输出模式</span>
            <select
              value={videoMode}
              onChange={(event) => onVideoModeChange(event.target.value as "compatible_mp4" | "source_auto")}
            >
              <option value="compatible_mp4">兼容 MP4（H.264 + AAC）</option>
              <option value="source_auto">原始质量（MP4 / MKV）</option>
            </select>
          </label>
          <label className="field">
            <span>共同可用格式</span>
            <select
              value={qualityId ?? ""}
              onChange={(event) => onQualityIdChange(event.target.value)}
              disabled={qualities.length === 0}
            >
              {qualities.length === 0 && <option value="">无共同可用格式</option>}
              {qualities.map((quality) => (
                <option value={quality.id} key={quality.id}>{quality.label}</option>
              ))}
            </select>
          </label>
          <p className="codec-note">
            {selectedQuality
              ? `${videoMode === "compatible_mp4" ? "MP4" : "MP4 / MKV"} · ${selectedQuality.video_codec} + ${selectedQuality.audio_codec ?? "最佳源音频"}`
              : "请先选择分 P"}
          </p>
          <button type="button" onClick={() => onCreate("video")} disabled={busy || !status.ffmpeg_available || selectedPageCount === 0 || qualityId === null}>
            下载 {selectedPageCount} P 视频
          </button>
        </article>
      </div>

      <div className="output-row">
        <label className="field output-field">
          <span>输出目录</span>
          <input value={outputDir} onChange={(event) => onOutputDirChange(event.target.value)} />
        </label>
        <button type="button" className="secondary-button" onClick={onOpenOutput}>打开目录</button>
      </div>
    </section>
  );
}
