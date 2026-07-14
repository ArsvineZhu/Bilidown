import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "../api";
import { AuthPanel } from "./AuthPanel";

const api = { uploadCookies: vi.fn() } as unknown as ApiClient;

afterEach(cleanup);

describe("AuthPanel", () => {
  it("shows the checked account and membership and can refresh", async () => {
    const onRefresh = vi.fn();
    render(
      <AuthPanel
        api={api}
        auth={{ kind: "browser", browser: "edge" }}
        authStatus={{ state: "active", username: "测试用户", vip_active: true, vip_label: "年度大会员" }}
        checking={false}
        checkError={null}
        onRefresh={onRefresh}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText("测试用户 · 年度大会员")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edge" })).toHaveClass("active");
    await userEvent.click(screen.getByRole("button", { name: "重新检查" }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("shows an authentication check error without disabling source selection", () => {
    render(
      <AuthPanel
        api={api}
        auth={{ kind: "browser", browser: "chrome" }}
        authStatus={null}
        checking={false}
        checkError="无法读取浏览器 Cookie"
        onRefresh={vi.fn()}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText("无法读取浏览器 Cookie")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "游客" })).toBeEnabled();
  });
});
