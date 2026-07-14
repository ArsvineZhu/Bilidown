from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"X-Bilidown-Token": token, "Origin": url.rsplit("/", 2)[0]},
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a packaged Bilidown executable")
    parser.add_argument("--executable", required=True, type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file():
        raise SystemExit(f"Packaged executable not found: {executable}")

    port = available_port()
    token = "portable-smoke-token"
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "BILIDOWN_NO_BROWSER": "1",
        "BILIDOWN_PORT": str(port),
        "BILIDOWN_SESSION_TOKEN": token,
    }
    process = subprocess.Popen([str(executable)], env=env)
    try:
        deadline = time.monotonic() + 20
        status: dict[str, object] | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Packaged app exited with code {process.returncode}")
            try:
                status = request_json(f"{origin}/api/status", token)
                break
            except (OSError, TimeoutError):
                time.sleep(0.2)
        if status is None:
            raise RuntimeError("Packaged app did not become ready within 20 seconds")
        if not status.get("ffmpeg_available"):
            raise RuntimeError("Packaged app did not find bundled FFmpeg and ffprobe")
        with urllib.request.urlopen(f"{origin}/", timeout=2) as response:
            csp = response.headers.get("Content-Security-Policy", "")
            if response.status != 200 or "default-src 'self'" not in csp:
                raise RuntimeError("Packaged frontend or CSP check failed")
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
