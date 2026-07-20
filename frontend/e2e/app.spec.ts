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

const resolvedResource = {
  canonical_url: resolvedVideo.canonical_url,
  kind: "video",
  title: resolvedVideo.title,
  uploader: resolvedVideo.uploader,
  thumbnail: null,
  items: [{
    index: 1,
    id: resolvedVideo.bvid,
    url: resolvedVideo.canonical_url,
    title: resolvedVideo.title,
    uploader: resolvedVideo.uploader,
    duration: resolvedVideo.duration,
    thumbnail: null,
    selected: true,
    live: false,
    branch: false,
  }],
  total_items: 1,
  truncated: false,
  experimental: false,
  warnings: [],
  video: resolvedVideo,
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
  await page.route("**/api/auth/auto", (route) => route.fulfill({ json: {
    auth: { kind: "guest" },
    status: { state: "guest", username: null, vip_active: false, vip_label: null },
  } }));
  await page.route("**/api/jobs", async (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: [] });
    return route.fulfill({ status: 201, json: {
      id: "job-1",
      status: "completed",
      request: route.request().postDataJSON(),
      progress: { phase: "completed", current_page: 1, downloaded_bytes: 100, total_bytes: 100, percent: 100, speed: null, eta: null },
      result_paths: ["C:\\Downloads\\Bilidown\\video.mp4"],
      item_results: [],
      error_code: null,
      error_message: null,
      created_at: "2026-07-14T00:00:00Z",
      updated_at: "2026-07-14T00:00:01Z",
    } });
  });
  await page.route("**/api/resources/resolve", (route) => route.fulfill({ json: resolvedResource }));

  await page.goto("/?token=e2e-token");
  await expect(page.locator(".hero-line")).toHaveCount(2);
  await page.getByLabel("Bilibili 媒体链接、BV 号或 AV 号").fill("BV1xx411c7mD");
  await page.getByRole("button", { name: "解析媒体" }).click();
  await expect(page.getByRole("heading", { name: "端到端测试视频" })).toBeVisible();
  await page.getByRole("button", { name: "下载 1 P 视频" }).click();
  await expect(page.getByText("已完成")).toBeVisible();
});

test("auto-selects Edge and confirms before exiting active jobs", async ({ page }) => {
  await page.route("**/api/status", (route) => route.fulfill({ json: {
    app_version: "0.1.1",
    yt_dlp_version: "test",
    ffmpeg_version: "test",
    ffmpeg_available: true,
    default_output_dir: "C:\\Downloads\\Bilidown",
  } }));
  await page.route("**/api/jobs", (route) => route.fulfill({ json: [{
    id: "job-1",
    status: "running",
    request: {
      credential: resolvedVideo.canonical_url,
      media_kind: "video",
      page_indices: [1],
      item_indices: [],
      item_urls: [],
      quality_height: 720,
      quality_id: "30064",
      video_mode: "compatible_mp4",
      audio_format: "original",
      auth: { kind: "guest" },
      output_dir: "C:\\Downloads\\Bilidown",
    },
    progress: { phase: "downloading", current_page: 1, downloaded_bytes: 1, total_bytes: 2, percent: 50, speed: null, eta: null },
    result_paths: [],
    item_results: [],
    error_code: null,
    error_message: null,
    created_at: "2026-07-14T00:00:00Z",
    updated_at: "2026-07-14T00:00:01Z",
  }] }));
  await page.route("**/api/auth/auto", (route) => route.fulfill({ json: {
    auth: { kind: "browser", browser: "edge" },
    status: { state: "active", username: "测试用户", vip_active: false, vip_label: null },
  } }));
  await page.route("**/api/quit", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/jobs/job-1/events", (route) => route.fulfill({ status: 200, body: "" }));

  await page.goto("/?token=e2e-token");
  await expect(page.getByText("Edge · 自动选择")).toBeVisible();
  await page.setViewportSize({ width: 320, height: 720 });
  for (const line of await page.locator(".hero-line").all()) {
    expect(await line.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  }
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "退出 Bilidown" }).click();
  await expect(page.getByRole("heading", { name: "Bilidown 已退出" })).toBeVisible();
});
