# Repository Guidelines

## Project Structure & Module Organization

Python backend code lives in `backend/bilidown/`: FastAPI routes, security middleware, input normalization, yt-dlp integration, jobs, and runtime discovery are separated by module. React/TypeScript code is under `frontend/src/`; component tests sit beside components, while Playwright flows live in `frontend/e2e/`. Python tests are in `tests/`. Packaging scripts, the PyInstaller spec, FFmpeg notices, and portable smoke checks are in `packaging/`. User and developer guides are indexed from `docs/README.md`.

## Build, Test, and Development Commands

Create a virtual environment, then install Python dependencies with `.venv\Scripts\python -m pip install -e ".[dev]"` on Windows or `.venv/bin/python -m pip install -e '.[dev]'` on macOS. Use `pnpm --dir frontend install --frozen-lockfile` for frontend dependencies. Run `python -m pytest`, `pnpm --dir frontend typecheck`, `pnpm --dir frontend test`, and `pnpm --dir frontend test:e2e` before submitting. `pnpm --dir frontend build` produces static assets. Portable builds use `packaging/build-portable.ps1` on Windows or `packaging/build-portable.sh` on macOS after the matching FFmpeg preparation script.

## Coding Style & Naming Conventions

Use four spaces, type hints, `snake_case` functions, and `PascalCase` models in Python. Use two spaces, named exports, `PascalCase` components, and `camelCase` values in TypeScript. Keep API models explicit and preserve existing route shapes. No repository-wide formatter is configured; avoid unrelated formatting churn and dependency changes.

## Testing Guidelines

Name Python tests `test_*.py`, component tests `*.test.tsx`, and browser specs `*.spec.ts`. Add focused regression coverage for every behavior change. Network tests must remain opt-in and must never require credentials in CI. There is no numeric coverage threshold; changed paths should be meaningfully exercised.

## Commit & Pull Request Guidelines

The repository has no established commit history, so use Conventional Commits such as `fix: handle macOS output opening` or `docs: add cookie guide`. Keep commits focused. Pull requests must explain intent, list verification commands, link relevant issues, disclose untested platforms, and include screenshots for visible UI changes.

## Security & Configuration Tips

Never commit cookies, `SESSDATA`, signed media URLs, Apple credentials, local paths, downloads, or build outputs. Preserve loopback-only binding, exact Origin checks, CSP, log redaction, and trusted-domain validation.
