# Bilidown

[简体中文](README.md) · [English](docs/en/README.md)

Bilidown 是一个仅在本机运行的 Bilibili 媒体下载与直播录制桌面应用。它支持普通投稿、番剧、课程、收藏夹/合集/系列/播放列表、互动视频分支、空间、音频、动态、稍后再看、BiliIntl，以及字幕和弹幕。

> 只下载你有权保存的内容，并遵守 Bilibili 服务条款与适用版权法律。本项目不会绕过 DRM、付费、会员、地区或账户权限。

## 五分钟开始

### 1. 从 Releases 下载

在 GitHub 项目页面打开 **Releases**，不要下载页面自动提供的 **Source code**。根据电脑选择：

- Windows 10/11 64 位：`.msi` 或 NSIS `.exe`
- Windows 10/11 64 位便携版：`Bilidown-<版本>-windows-x64-portable.zip`
- Apple Silicon Mac（M1/M2/M3/M4 等）：`.dmg`

下载同一 Release 的 `SHA256SUMS.txt` 后可校验文件：

```powershell
# Windows PowerShell
Get-FileHash .\Bilidown-1.0.0-windows-x64-portable.zip -Algorithm SHA256
```

```bash
# macOS Terminal
shasum -a 256 Bilidown-0.1.1-macos-arm64.app.zip
```

结果应与 `SHA256SUMS.txt` 中对应行完全一致。

### 2. 解压并启动

- Windows 安装版：运行 `.msi` 或 NSIS `.exe`，按安装向导完成安装。
- Windows 便携版：完整解压 `Bilidown-<版本>-windows-x64-portable.zip`，双击目录中的 `Bilidown.exe`。不要只从压缩包预览窗口运行，也不要移动或删除同目录的 `bilidown-backend.exe`。
- macOS：解压后把 `Bilidown.app` 移到“应用程序”，再打开。未公证构建首次启动时，请按[故障排查](docs/troubleshooting.md#macos-提示无法验证开发者)处理，不要关闭整个 Gatekeeper。

程序以原生桌面窗口运行，后台仅监听 `127.0.0.1`。关闭窗口会最小化到系统托盘；托盘菜单可重新打开、调整空闲退出时间或彻底退出。默认无活动 30 分钟后退出，任务或直播录制进行中不会自动退出。

### 3. 解析并下载

1. 保持“游客”，或使用应用内二维码登录；`cookies.txt` 和 Firefox 直读仍作为高级选项。
2. 粘贴受支持的 Bilibili 链接并点击“解析媒体”，预览后勾选最多 100 项。
3. 下载封面、音频、视频、字幕、弹幕 XML/ASS；直播链接使用独立录制器。

完整覆盖范围与限制见[媒体支持矩阵](docs/media-support.md)。

## 应用元信息

| 项目 | 值 |
| --- | --- |
| 产品名 | Bilidown |
| 版本 | 1.0.0 |
| 作者与发布者 | Arsvine Zhu |
| 应用标识 | `io.github.arsvinezhu.bilidown` |
| 版权 | Copyright © 2026 Arsvine Zhu |
| 许可证 | MIT（FFmpeg/LAME/yt-dlp 适用各自许可证） |

## 文档导航

- [分级文档入口](docs/README.md)
- [安装与基本使用](docs/getting-started.md)
- [登录与 Cookie](docs/login-and-cookies.md)
- [画质、编码与音频格式](docs/formats-and-quality.md)
- [媒体支持矩阵与限制](docs/media-support.md)
- [故障排查](docs/troubleshooting.md)
- [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

## 开发者快速命令

### 环境准备

需要 Python 3.12/3.13、Node.js 22、pnpm。macOS 构建桌面应用还需要 Rust 和 pkg-config：

```bash
# macOS 安装额外系统依赖
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
brew install pkg-config
```

### 安装项目依赖

```powershell
# Windows（标准）
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"

# Windows（uv）
uv venv
uv pip install -e ".[dev]"
```

```bash
# macOS / Linux（标准）
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

# macOS / Linux（uv）
uv venv
uv pip install -e ".[dev]"
```

```bash
# 前端（所有平台通用）
pnpm --dir frontend install --frozen-lockfile
```

### 运行测试

```bash
.venv/bin/python -m pytest        # Python 测试
pnpm --dir frontend typecheck      # TypeScript 类型检查
pnpm --dir frontend test           # 前端单元测试
pnpm --dir frontend build          # 前端生产构建
```

### 构建桌面应用

```powershell
# Windows
packaging\prepare-ffmpeg.ps1
packaging\build-desktop.ps1 -Python .\.venv\Scripts\python.exe
```

```bash
# macOS (Apple Silicon)
bash packaging/prepare-ffmpeg-macos.sh
PYTHON=.venv/bin/python bash packaging/build-desktop.sh
```

产物位于 `src-tauri/target/release/bundle/`。完整说明见[开发环境](docs/development.md)和[构建与发布](docs/building-and-releasing.md)。

Bilidown 使用 MIT License；随包 FFmpeg/LAME 的许可证与对应源码信息见 `packaging/THIRD_PARTY_NOTICES.txt` 和 Release 源码归档。
