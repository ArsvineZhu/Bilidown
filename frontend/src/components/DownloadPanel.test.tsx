import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { AppStatus, QualityOption } from "../api";
import { DownloadPanel } from "./DownloadPanel";

const status: AppStatus = {
  app_version: "0.1.0",
  yt_dlp_version: "test",
  ffmpeg_version: "test",
  ffmpeg_available: true,
  default_output_dir: "C:\\Downloads",
};

const quality: QualityOption = {
  id: "120",
  label: "4K 超高清 · HEVC · 12.0 Mbps · HDR10",
  height: 2160,
  width: 3840,
  fps: 60,
  quality_code: 120,
  format_name: "4K 超高清",
  bitrate_kbps: 12000,
  dynamic_range: "HDR10",
  codec_family: "HEVC",
  video_codec: "hvc1.2.4.L153",
  audio_codec: "ec-3",
  container: "mp4",
  compatibility: "fallback",
};

describe("DownloadPanel", () => {
  it("shows exact advanced quality labels and source formats", async () => {
    const onVideoModeChange = vi.fn();
    const onAudioFormatChange = vi.fn();
    render(
      <DownloadPanel
        status={status}
        outputDir={status.default_output_dir}
        onOutputDirChange={vi.fn()}
        qualities={[quality]}
        qualityId={quality.id}
        onQualityIdChange={vi.fn()}
        videoMode="source_auto"
        onVideoModeChange={onVideoModeChange}
        audioFormat="m4a"
        onAudioFormatChange={onAudioFormatChange}
        selectedPageCount={1}
        busy={false}
        onCreate={vi.fn()}
        onOpenOutput={vi.fn()}
      />,
    );

    expect(screen.getByRole("option", { name: quality.label })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("输出模式"), "compatible_mp4");
    expect(onVideoModeChange).toHaveBeenCalledWith("compatible_mp4");
    await userEvent.selectOptions(screen.getByLabelText("输出格式"), "best_source");
    expect(onAudioFormatChange).toHaveBeenCalledWith("best_source");
  });
});
