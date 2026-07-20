# Repository Guidelines

## Project Structure & Module Organization

Python backend code lives in `backend/bilidown/`: FastAPI routes, security middleware, input normalization, yt-dlp integration, jobs, and runtime discovery are separated by module. React/TypeScript code is under `frontend/src/`; component tests sit beside components, while Playwright flows live in `frontend/e2e/`. The Tauri desktop shell is in `src-tauri/`, and Python tests are in `tests/`. Packaging scripts, the sidecar spec, and FFmpeg notices are in `packaging/`. User and developer guides are indexed from `docs/README.md`.

## Build, Test, and Development Commands

### Python virtual environment — two supported methods, either works

If `uv` is available on the machine, prefer it:

```bash
uv venv
uv pip install -e ".[dev]"
```

If `uv` is NOT available, use the standard approach:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python`.

### Frontend dependencies (all platforms)

```bash
pnpm --dir frontend install --frozen-lockfile
```

### Running tests before submitting

```bash
python -m pytest
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend test:e2e
```

`pnpm --dir frontend build` produces static assets.

### Building the desktop app (macOS)

Prerequisites: Rust and pkg-config must be installed on the machine before building.

```bash
# Install Rust if not already installed
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install pkg-config via Homebrew (if not already installed)
brew install pkg-config

# Compile FFmpeg + LAME from source into .tools/ffmpeg/
bash packaging/prepare-ffmpeg-macos.sh

# Build the .app and .dmg
PYTHON=.venv/bin/python bash packaging/build-desktop.sh
```

### Building the desktop app (Windows)

```powershell
packaging\prepare-ffmpeg.ps1
packaging\build-desktop.ps1 -Python .\.venv\Scripts\python.exe
```

Outputs go to `src-tauri/target/release/bundle/`.

## Coding Style & Naming Conventions

Use four spaces, type hints, `snake_case` functions, and `PascalCase` models in Python. Use two spaces, named exports, `PascalCase` components, and `camelCase` values in TypeScript. Keep API models explicit and preserve existing route shapes. No repository-wide formatter is configured; avoid unrelated formatting churn and dependency changes.

## Testing Guidelines

Name Python tests `test_*.py`, component tests `*.test.tsx`, and browser specs `*.spec.ts`. Add focused regression coverage for every behavior change. Network tests must remain opt-in and must never require credentials in CI. There is no numeric coverage threshold; changed paths should be meaningfully exercised.

## Commit & Pull Request Guidelines

The repository has no established commit history, so use Conventional Commits such as `fix: handle macOS output opening` or `docs: add cookie guide`. Keep commits focused. Pull requests must explain intent, list verification commands, link relevant issues, disclose untested platforms, and include screenshots for visible UI changes.

## Security & Configuration Tips

Never commit cookies, `SESSDATA`, signed media URLs, Apple credentials, local paths, downloads, or build outputs. Preserve loopback-only binding, exact Origin checks, CSP, log redaction, and trusted-domain validation.
