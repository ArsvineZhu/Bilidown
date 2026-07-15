# 构建与发布

PyInstaller 不是交叉编译器：Windows 包在 Windows 构建，两个 macOS 包分别在对应架构构建。版本同时存在于 `pyproject.toml` 和 `backend/bilidown/__init__.py`，发布前必须一致。

## Windows x64

```powershell
packaging\prepare-ffmpeg.ps1
packaging\build-portable.ps1 -Python .\.venv\Scripts\python.exe
```

FFmpeg 脚本下载固定 BtbN LGPL 构建并校验 SHA-256。产物为 `dist/Bilidown-<版本>-windows-x64.zip` 及 `.sha256`。

## macOS 原生包

安装 Xcode Command Line Tools、Python、Node、pnpm 和 `pkg-config`，在目标架构机器运行：

```bash
bash packaging/prepare-ffmpeg-macos.sh
PYTHON=.venv/bin/python bash packaging/build-portable.sh
```

FFmpeg 8.1.2 与 LAME 3.100 从固定源码和校验和构建，目标最低 macOS 13。正式产物为 `Bilidown-<版本>-macos-arm64.app.zip`。默认使用 ad-hoc 签名。

## GitHub Actions

`CI` 在 PR 和 main/master 推送上运行 pytest、TypeScript、Vitest、Vite 与 Playwright。`Portable builds` 可手动触发；未填写版本时使用 `dev-<短 SHA>`，两个便携包和第三方源码作为 artifacts 保留 14 天。

推送与项目版本完全一致的 `vX.Y.Z` 标签创建正式 Release；`vX.Y.Z-rc.N` 仅在项目版本本身也是该预发布版本时创建 prerelease。Release 包含 Windows x64、macOS arm64 两个便携 ZIP、第三方源码包和 `SHA256SUMS.txt`。

## Apple 签名与公证

以下 GitHub Secrets 全部存在时，工作流导入 Developer ID 证书、启用 hardened runtime、提交 Apple notary service 并 staple：

- `APPLE_CERTIFICATE_BASE64`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_TEAM_ID`
- `APPLE_ID`
- `APPLE_APP_PASSWORD`

缺少任意一项时退回 ad-hoc 签名，并随 artifact 写入 `SIGNING_STATUS`。不要把证书、密码、Cookie 或会话令牌写进 workflow、日志或仓库。

## 发布前验收

确认 CI 全绿、两个便携包均通过 `packaging/smoke-portable.py`、macOS 架构和最低版本正确、签名状态符合预期、许可证与源码归档齐全。真实 Bilibili/4K 测试在本机执行，不作为 Release 阻塞型 CI。
