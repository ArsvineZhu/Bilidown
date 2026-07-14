# 安全政策

## 支持范围

安全修复面向当前默认分支和最新 GitHub Release。旧便携包可能包含过期的 yt-dlp、Python 或 FFmpeg；发现问题后应先确认最新版是否仍可复现。

## 私密报告

以下问题请勿先创建公开 Issue：Cookie/`SESSDATA` 泄漏、会话令牌绕过、任意文件读写、短链 SSRF、签名媒体 URL 泄漏、恶意文件名逃逸、便携构建供应链或签名问题。

优先使用仓库 **Security** 页面中的 **Report a vulnerability** 私密报告。若该功能未启用，请创建不含技术细节的普通 Issue，请求维护者提供私密联系方式；不要附 PoC、Cookie、账号资料或敏感日志。

报告应包含：受影响版本与平台、影响、最小复现步骤、必要的脱敏日志、你已采取的缓解措施。请给维护者合理确认和修复时间后再讨论公开披露。

## 使用者自查

- 只从 GitHub Releases 下载，并核对 `SHA256SUMS.txt`。
- 不要从他人处接收 `cookies.txt`，也不要分享自己的文件。
- macOS 未公证包只应在校验来源后通过“仍要打开”放行，不要全局关闭 Gatekeeper。
- 怀疑 Cookie 泄漏时立即退出 Bilibili 所有设备并修改密码。

Bilidown 不收集遥测，也不提供远程服务。有关本地令牌、Cookie 和日志边界，参见[安全与隐私](docs/security-and-privacy.md)。
