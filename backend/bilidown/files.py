from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def sanitize_filename(value: str, *, max_length: int = 160) -> str:
    cleaned = _INVALID_WINDOWS_CHARS.sub("_", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "untitled"
    stem = cleaned.split(".", 1)[0].upper()
    if stem in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned[:max_length].rstrip(" .") or "untitled"


def ensure_output_directory(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("输出目录必须是绝对路径")
    path.mkdir(parents=True, exist_ok=True)
    probe = path / f".bilidown-write-{os.getpid()}"
    try:
        probe.write_bytes(b"")
    except OSError as exc:
        raise ValueError("输出目录不可写") from exc
    finally:
        probe.unlink(missing_ok=True)
    return path.resolve()


def move_without_overwrite(source: Path, destination_dir: Path) -> Path:
    candidate = destination_dir / source.name
    counter = 1
    while candidate.exists():
        candidate = destination_dir / f"{source.stem} ({counter}){source.suffix}"
        counter += 1
    shutil.move(str(source), str(candidate))
    return candidate

