import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ResolvedVideo } from "../api";
import { VideoPreview } from "./VideoPreview";

const video: ResolvedVideo = {
  canonical_url: "https://www.bilibili.com/video/BV1xx411c7mD",
  bvid: "BV1xx411c7mD",
  aid: 1,
  title: "测试视频",
  uploader: "测试 UP 主",
  thumbnail: null,
  duration: 125,
  selected_page: 1,
  pages: [
    { index: 1, cid: 11, title: "第一部分", duration: 60, qualities: [] },
    { index: 2, cid: 12, title: "第二部分", duration: 65, qualities: [] },
  ],
};

describe("VideoPreview", () => {
  it("renders metadata and toggles all pages", async () => {
    const onChange = vi.fn();
    render(<VideoPreview video={video} selectedPages={new Set([1])} onSelectedPagesChange={onChange} />);
    expect(screen.getByText("测试视频")).toBeInTheDocument();
    expect(screen.getByText("第一部分")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "选择全部" }));
    expect([...onChange.mock.calls[0][0]]).toEqual([1, 2]);
  });
});

