# 登录与 Cookie

Bilidown 不提供账号密码登录，也不会绕过 Bilibili 权限。它只复用本机浏览器已有登录态，或读取你主动提供的 Netscape `cookies.txt`。

## 游客

默认“游客”不读取任何 Cookie。公开视频通常可解析 360P–1080P，实际结果由投稿和 Bilibili 当前策略决定。4K、高码率、HDR、Dolby 或会员音频可能不会返回。

## 本机浏览器

选择 Chrome、Edge 或 Firefox 后，应用通过 yt-dlp 读取该浏览器的 Bilibili Cookie，并检查 `/x/web-interface/nav`。状态卡会显示：

- 登录来源；
- “活跃”或“未检测到有效登录态”；
- 账号昵称；
- 普通账号或 Bilibili 返回的大会员标签。

不会返回头像、UID、会员到期时间、`SESSDATA` 或完整 Cookie。Profile 留空时使用浏览器最近使用的配置；多 Profile 用户可填写浏览器的实际 Profile 名称。

Chrome/Edge 在 Windows 上可能因 DPAPI 或应用绑定加密无法解密。先完全退出浏览器（包括后台进程）后重新检查；仍失败时使用 Firefox 登录态或 `cookies.txt`。

## `cookies.txt`

文件必须是 Netscape Cookie 格式。导出时只选择 `bilibili.com`，不要使用来历不明的扩展，也不要把文件上传到 Issue、网盘或聊天工具。

点击“载入 cookies.txt”后，后端只保留 Bilibili 域条目并建立内存会话。原始上传内容不写入历史记录；退出 Bilidown 后会话失效。若文件包含其他网站 Cookie，它们会被丢弃。

## 状态与画质的关系

“年度大会员”只说明 Cookie 当前有效，并不保证每个投稿都有 4K。画质必须同时满足：投稿确实上传该源、账号有权访问、地区允许、所选分 P 返回该格式。切换登录来源后重新解析视频，旧解析结果不会自动升级。

## 安全处理

- 不要截图或复制 Cookie 内容。
- 怀疑泄漏时立即在 Bilibili 退出所有设备并修改密码。
- 公共电脑上不要加载个人 Cookie。
- CI 和 GitHub Secrets 中禁止保存会员 Cookie；真实会员测试只在受控本机显式运行。
