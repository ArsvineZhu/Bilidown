# Bilidown

Bilidown 是一个仅在本机运行的 Bilibili 普通投稿下载器。输入 BV 号、AV 号、视频链接或 `b23.tv` 短链，即可下载原始封面、音频或账号实际可访问的视频画质。

> 只下载你有权保存的内容，并遵守 Bilibili 服务条款与适用版权法律。本项目不会绕过 DRM、付费、会员、地区或账户权限。

## 五分钟开始

### 1. 从 Releases 下载

在 GitHub 项目页面打开 **Releases**，不要下载页面自动提供的 **Source code**。根据电脑选择：

- Windows 10/11 64 位：`Bilidown-<版本>-windows-x64.zip`
- Apple Silicon Mac（M1/M2/M3/M4 等）：`Bilidown-<版本>-macos-arm64.app.zip`
- Intel Mac：`Bilidown-<版本>-macos-x86_64.app.zip`

下载同一 Release 的 `SHA256SUMS.txt` 后可校验文件：

```powershell
# Windows PowerShell
Get-FileHash .\Bilidown-0.1.0-windows-x64.zip -Algorithm SHA256
```

```bash
# macOS Terminal
shasum -a 256 Bilidown-0.1.0-macos-arm64.app.zip
```

结果应与 `SHA256SUMS.txt` 中对应行完全一致。

### 2. 解压并启动

- Windows：完整解压 ZIP，双击 `Bilidown\Bilidown.exe`。不要只从压缩包预览窗口运行。
- macOS：解压后把 `Bilidown.app` 移到“应用程序”，再打开。未公证构建首次启动时，请按[故障排查](docs/troubleshooting.md#macos-提示无法验证开发者)处理，不要关闭整个 Gatekeeper。

程序会打开默认浏览器，并且只监听 `127.0.0.1`。浏览器页面关闭后，后台进程不会自动退出；可在任务管理器或活动监视器中结束 `Bilidown`。

### 3. 解析并下载

1. 保持“游客”，或选择 Chrome、Edge、Firefox / 导入 `cookies.txt`。
2. 粘贴视频凭据并点击“解析视频”，再选择分 P、格式和输出目录。
3. 分别点击下载封面、音频或视频，在任务队列等待完成。

## 文档导航

- [分级文档入口](docs/README.md)
- [安装与基本使用](docs/getting-started.md)
- [登录与 Cookie](docs/login-and-cookies.md)
- [画质、编码与音频格式](docs/formats-and-quality.md)
- [故障排查](docs/troubleshooting.md)
- [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

## 开发者快速命令

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
pnpm --dir frontend install --frozen-lockfile
.venv\Scripts\python -m pytest
pnpm --dir frontend test
pnpm --dir frontend build
```

macOS/Linux 将 `.venv\Scripts\python` 替换为 `.venv/bin/python`。完整说明见[开发环境](docs/development.md)和[构建与发布](docs/building-and-releasing.md)。

Bilidown 使用 MIT License；随包 FFmpeg/LAME 的许可证与对应源码信息见 `packaging/THIRD_PARTY_NOTICES.txt` 和 Release 源码归档。
