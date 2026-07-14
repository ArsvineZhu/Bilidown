import { expect, test } from "@playwright/test";

const resolvedVideo = {
  canonical_url: "https://www.bilibili.com/video/BV1xx411c7mD",
  bvid: "BV1xx411c7mD",
  aid: 1,
  title: "端到端测试视频",
  uploader: "Bilidown Test",
  thumbnail: null,
  duration: 90,
  selected_page: 1,
  pages: [
    {
      index: 1,
      cid: 10,
      title: "第一部分",
      duration: 90,
      qualities: [
        {
          id: "30064",
          label: "720P",
          height: 720,
          width: 1280,
          fps: 30,
          quality_code: 64,
          format_name: "720P 准高清",
          bitrate_kbps: 1800,
          dynamic_range: "SDR",
          codec_family: "H.264",
          video_codec: "avc1.64001f",
          audio_codec: "mp4a.40.2",
          container: "mp4",
          compatibility: "preferred",
        },
      ],
    },
  ],
};

test("resolve and create a video task", async ({ page }) => {
  await page.route("**/api/status", (route) => route.fulfill({ json: {
    app_version: "0.1.0",
    yt_dlp_version: "test",
    ffmpeg_version: "test",
    ffmpeg_available: true,
    default_output_dir: "C:\\Downloads\\Bilidown",
  } }));
  await page.route("**/api/auth/status", (route) => route.fulfill({ json: {
    state: "guest",
    username: null,
    vip_active: false,
    vip_label: null,
  } }));
  await page.route("**/api/jobs", async (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: [] });
    return route.fulfill({ status: 201, json: {
      id: "job-1",
      status: "completed",
      request: route.request().postDataJSON(),
      progress: { phase: "completed", current_page: 1, downloaded_bytes: 100, total_bytes: 100, percent: 100, speed: null, eta: null },
      result_paths: ["C:\\Downloads\\Bilidown\\video.mp4"],
      error_code: null,
      error_message: null,
      created_at: "2026-07-14T00:00:00Z",
      updated_at: "2026-07-14T00:00:01Z",
    } });
  });
  await page.route("**/api/resolve", (route) => route.fulfill({ json: resolvedVideo }));

  await page.goto("/?token=e2e-token");
  await page.getByLabel("BV 号、AV 号或视频链接").fill("BV1xx411c7mD");
  await page.getByRole("button", { name: "解析视频" }).click();
  await expect(page.getByRole("heading", { name: "端到端测试视频" })).toBeVisible();
  await page.getByRole("button", { name: "下载 1 P 视频" }).click();
  await expect(page.getByText("已完成")).toBeVisible();
});
