# 开发环境

## 依赖

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.12 或 3.13 | CI 使用 3.13 |
| Node.js | 22 | |
| pnpm | | 前端包管理 |
| Rust（stable） | 含 rustfmt、clippy | 仅桌面构建需要 |
| pkg-config | | 仅 macOS 桌面构建需要 |
| FFmpeg / ffprobe | | 媒体集成测试和 sidecar 打包需要 |

安装 Rust：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

安装 pkg-config（仅 macOS 桌面构建需要，需提前安装 [Homebrew](https://brew.sh)）：

```bash
brew install pkg-config
```

## 初始化

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
pnpm --dir frontend build
.venv/bin/python -m bilidown.launcher

## 前后端开发模式

在两个终端分别运行：

**终端 1 — 后端：**

```powershell
# Windows
$env:BILIDOWN_DEV_TOKEN = "dev-token"
$env:BILIDOWN_DEV_ORIGIN = "http://127.0.0.1:5173"
.venv\Scripts\python -m bilidown.devserver
```

```bash
# macOS / Linux
export BILIDOWN_DEV_TOKEN=dev-token
export BILIDOWN_DEV_ORIGIN=http://127.0.0.1:5173
.venv/bin/python -m bilidown.devserver
```

**终端 2 — 前端：**

```bash
pnpm --dir frontend dev
```

访问 `http://127.0.0.1:5173/?token=dev-token`。

## 测试

```powershell
# Windows
.venv\Scripts\python -m pytest
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
cd src-tauri
cargo fmt --all --check
cargo clippy --all-targets -- -D warnings
```

```bash
# macOS / Linux
.venv/bin/python -m pytest
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
cd src-tauri
cargo fmt --all --check
cargo clippy --all-targets -- -D warnings
```

网络测试默认跳过。任意公开视频可设置 `BILIDOWN_SMOKE_URL`；固定样例测试设置 `BILIDOWN_KNOWN_NETWORK_SMOKE=1`。会员 4K 仅在受控本机额外设置 `BILIDOWN_SMOKE_BROWSER=firefox` 等有效登录来源，禁止向 CI 提交 Cookie。

代码风格见 [AGENTS.md](../AGENTS.md)。不要运行会重写整个仓库的格式化命令，也不要提交 `.venv/`、`.tools/`、`dist/`、`build/`、下载结果或浏览器状态。

## 构建桌面应用

PyInstaller 将 Python 后端打包为单文件 sidecar，Tauri 再生成原生安装包。详见[构建与发布](building-and-releasing.md)。

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

产物：`src-tauri/target/release/bundle/`，包含 `.app`、`.dmg`（macOS）或 `.exe`、`.msi`（Windows）。
