# 构建与发布

PyInstaller 先生成单文件 Python sidecar，Tauri 再生成原生安装包。Windows 和 macOS 必须分别原生构建。版本同时存在于 `pyproject.toml`、Python 包、`src-tauri/Cargo.toml` 和 `src-tauri/tauri.conf.json`，发布前必须一致。

## Windows x64

```powershell
packaging\prepare-ffmpeg.ps1
packaging\build-desktop.ps1 -Python .\.venv\Scripts\python.exe
```

FFmpeg 脚本下载固定 BtbN LGPL 构建并校验 SHA-256。产物位于 `src-tauri/target/release/bundle/`，包括 NSIS `.exe` 和 MSI。

### Windows 便携版

```powershell
packaging\build-portable.ps1 -Python .\.venv\Scripts\python.exe
```

脚本会生成 `dist/Bilidown-<版本>-windows-x64-portable.zip` 与同名 `.sha256` 文件。便携包包含 Tauri 主程序、Python sidecar、使用说明、包内 `SHA256SUMS.txt` 和许可证/FFmpeg 来源文件；它不写注册表，也不安装服务。若已运行 `build-desktop.ps1`，可使用 `-SkipBuild` 复用同一轮编译产物：

```powershell
packaging\build-portable.ps1 -Python .\.venv\Scripts\python.exe -SkipBuild
```

## macOS 原生包

安装 Xcode Command Line Tools、Python、Node、pnpm 和 `pkg-config`，在目标架构机器运行：

```bash
bash packaging/prepare-ffmpeg-macos.sh
PYTHON=.venv/bin/python bash packaging/build-desktop.sh
```

FFmpeg 8.1.2 与 LAME 3.100 从固定源码和校验和构建，目标最低 macOS 13。Tauri 生成 `.app` 和 `.dmg`；默认使用 ad-hoc 签名。

## GitHub Actions

`CI` 在 PR 和 main/master 推送上运行 pytest、严格 Python/TypeScript/Rust 检查、Vitest、Vite 与 Playwright。`Desktop builds` 可手动触发并在 Windows/macOS 构建原生安装包。

推送与项目版本完全一致的 `vX.Y.Z` 标签创建正式 Release；`vX.Y.Z-rc.N` 仅在项目版本本身也是该预发布版本时创建 prerelease。Release 包含 Windows x64 NSIS/MSI/便携 ZIP、macOS arm64 DMG、第三方源码包和 `SHA256SUMS.txt`。

## Apple 签名与公证

以下 GitHub Secrets 全部存在时，工作流导入 Developer ID 证书、启用 hardened runtime、提交 Apple notary service 并 staple：

- `APPLE_CERTIFICATE_BASE64`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_TEAM_ID`
- `APPLE_ID`
- `APPLE_APP_PASSWORD`

缺少任意一项时退回 ad-hoc 签名，并随 artifact 写入 `SIGNING_STATUS`。不要把证书、密码、Cookie 或会话令牌写进 workflow、日志或仓库。

## 发布前验收

确认 CI 全绿、Windows NSIS/MSI/便携 ZIP 与 macOS DMG 都已生成、sidecar 能随桌面壳启动、便携 ZIP 解压后主程序与 sidecar 同级、macOS 架构和最低版本正确、签名状态符合预期、许可证与源码归档齐全。真实 Bilibili/4K 测试在本机执行，不作为 Release 阻塞型 CI。
