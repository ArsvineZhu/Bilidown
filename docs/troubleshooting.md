# 故障排查

## Windows SmartScreen 阻止启动

先确认 ZIP 来自项目 Releases，并核对 `SHA256SUMS.txt`。在 SmartScreen 页面选择“更多信息”→“仍要运行”。不要关闭系统的整体安全防护。若 EXE 仍无法启动，确认已完整解压整个 `Bilidown` 文件夹。

## macOS 提示无法验证开发者

ad-hoc 签名包未经过 Apple 公证时可能出现此提示。确认下载来源和 SHA-256 后：

1. 在 Finder 中按住 Control 点击 `Bilidown.app`，选择“打开”；或
2. 打开“系统设置”→“隐私与安全性”，在被阻止的应用旁选择“仍要打开”。

不要执行关闭 Gatekeeper 的全局命令。正式签名且公证的 Release 不需要这些步骤。

## 页面没有打开

检查任务管理器/活动监视器中是否有 Bilidown，防火墙是否阻止本地环回连接。手动访问地址必须包含当前会话令牌；最简单的处理是结束进程后重新启动。程序只支持 `127.0.0.1`，不能从手机或局域网访问。

## 封面不显示或不能下载

可信的 `bilibili.com`/`hdslb.com` HTTP 地址会升级为 HTTPS。其他域名会被安全过滤。先重新解析；如果视频和音频正常而封面为空，通常是上游没有返回可信封面，不要绕过域名校验。

## 浏览器 Cookie 解密失败

完全退出 Chrome/Edge，包括系统托盘与后台进程，再点击“重新检查”。仍失败时尝试 Firefox 或 Netscape `cookies.txt`。macOS 首次读取浏览器 Cookie 时可能要求钥匙串授权，应核对请求程序后再允许。

## 已是大会员但没有 4K/高码率

确认状态卡显示昵称和会员标签，然后重新解析。投稿源、分 P、地区与账户权限必须同时支持该格式。可用 `BV1NGZtBwELa` 做会员 4K 解析测试；不要用实际上限 1080P 的投稿判断 4K 功能。

## FFmpeg 不可用或合并失败

官方便携包内置 `ffmpeg` 和 `ffprobe`。不要只复制主 EXE/.app 内部单个文件。重新下载并完整解压；自行构建时先运行对应平台的 FFmpeg 准备脚本。

## 412、429、网络超时

Bilibili 可能临时限制请求。暂停频繁解析，稍后重试；关闭代理或切换稳定网络。不要在 CI 中高频运行真实站点测试。站点结构变化时可能需要升级 Bilidown/yt-dlp。

## 日志位置

启动异常日志：

- Windows：`%LOCALAPPDATA%\Bilidown\startup-error.log`
- macOS：`~/Library/Logs/Bilidown/startup-error.log`

提交 Issue 前请删除用户名、完整本地路径和任何 Cookie/签名 URL。参见[安全政策](../SECURITY.md)。
