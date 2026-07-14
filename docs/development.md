# 开发环境

## 依赖

- Python 3.12 或 3.13；CI 使用 3.13。
- Node.js 22、pnpm 11.8.0。
- FFmpeg/ffprobe；媒体集成测试和下载需要。

## 初始化

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
.venv\Scripts\python -m bilidown.launcher
```

macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
.venv/bin/python -m bilidown.launcher
```

## 前后端开发模式

后端：

```powershell
$env:BILIDOWN_DEV_TOKEN = "dev-token"
$env:BILIDOWN_DEV_ORIGIN = "http://127.0.0.1:5173"
.venv\Scripts\python -m bilidown.devserver
```

macOS 使用 `export BILIDOWN_DEV_TOKEN=dev-token`、`export BILIDOWN_DEV_ORIGIN=http://127.0.0.1:5173`。另一终端运行：

```bash
pnpm --dir frontend dev
```

访问 `http://127.0.0.1:5173/?token=dev-token`。

## 测试

```powershell
.venv\Scripts\python -m pytest
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

网络测试默认跳过。任意公开视频可设置 `BILIDOWN_SMOKE_URL`；固定样例测试设置 `BILIDOWN_KNOWN_NETWORK_SMOKE=1`。会员 4K 仅在受控本机额外设置 `BILIDOWN_SMOKE_BROWSER=firefox` 等有效登录来源，禁止向 CI 提交 Cookie。

代码风格见 [AGENTS.md](../AGENTS.md)。不要运行会重写整个仓库的格式化命令，也不要提交 `.venv/`、`.tools/`、`dist/`、`build/`、下载结果或浏览器状态。
