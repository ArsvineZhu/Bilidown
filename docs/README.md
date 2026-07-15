# Bilidown 分级文档

按你的当前目标选择层级，无需从头读完。

## Level 0：第一次下载

先阅读根目录 [README](../README.md) 的“五分钟开始”。它解释如何从 GitHub Releases 选择 Windows 或 Apple Silicon 包，以及如何校验 SHA-256。

## Level 1：基本使用

- [安装与基本使用](getting-started.md)：启动、输入视频、选择分 P、设置输出目录、查看任务。
- [安全与隐私](security-and-privacy.md)：本地监听、会话令牌、Cookie 生命周期和使用边界。

## Level 2：登录与格式

- [登录与 Cookie](login-and-cookies.md)：游客、浏览器 Cookie、`cookies.txt`、大会员状态。
- [画质、编码与音频格式](formats-and-quality.md)：兼容 MP4、原始质量、4K/HDR/Dolby、M4A/MP3。

## Level 3：出现问题

- [故障排查](troubleshooting.md)：SmartScreen、Gatekeeper、Cookie 解密、登录失效、FFmpeg、网络和日志。

## Developer：开发与发布

- [架构说明](architecture.md)：前后端、任务队列、安全边界和下载流程。
- [开发环境](development.md)：依赖、命令、测试和网络冒烟。
- [构建与发布](building-and-releasing.md)：Windows/macOS 便携包、签名、公证、CI 和版本标签。
- [贡献指南](../CONTRIBUTING.md) · [Repository Guidelines](../AGENTS.md) · [安全政策](../SECURITY.md)

文档中的 `<版本>`、`<owner>` 等尖括号文本是占位符，请替换为实际值，不要原样输入。
