import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { JobView } from "../api";
import { JobList } from "./JobList";

const job: JobView = {
  id: "job-1",
  status: "running",
  request: {
    credential: "BV1xx411c7mD",
    media_kind: "video",
    page_indices: [1],
    item_indices: [],
    item_urls: [],
    quality_height: 720,
    quality_id: "30064",
    video_mode: "compatible_mp4",
    audio_format: "original",
    auth: { kind: "guest" },
    output_dir: "C:\\Downloads",
  },
  progress: {
    phase: "downloading",
    current_page: 1,
    downloaded_bytes: 1024,
    total_bytes: 2048,
    percent: 50,
    speed: 512,
    eta: 2,
  },
  result_paths: [],
  item_results: [],
  error_code: null,
  error_message: null,
  created_at: "2026-07-14T00:00:00Z",
  updated_at: "2026-07-14T00:00:01Z",
};

describe("JobList", () => {
  it("shows running progress and cancel action", () => {
    render(<JobList jobs={[job]} onCancel={vi.fn()} onRetry={vi.fn()} />);
    expect(screen.getByText("720P 视频")).toBeInTheDocument();
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消" })).toBeInTheDocument();
  });
});
