from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def frontend_dist() -> Path:
    bundled = application_root() / "frontend" / "dist"
    if bundled.exists():
        return bundled
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def find_ffmpeg_binary(name: str = "ffmpeg") -> str | None:
    executable = f"{name}.exe" if os.name == "nt" else name
    candidates = [
        application_root() / "ffmpeg" / "bin" / executable,
        Path(__file__).resolve().parents[2] / ".tools" / "ffmpeg" / "bin" / executable,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def ffmpeg_location() -> str | None:
    binary = find_ffmpeg_binary("ffmpeg")
    return str(Path(binary).parent) if binary else None


def ffmpeg_version() -> str | None:
    binary = find_ffmpeg_binary("ffmpeg")
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        return None
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    return first_line.removeprefix("ffmpeg version ").strip() or None
