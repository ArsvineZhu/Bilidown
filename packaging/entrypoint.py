from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import traceback
from pathlib import Path


def _diagnostic_directory() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA", Path.home())) / "Bilidown"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "Bilidown"
    return Path.home() / ".local" / "state" / "Bilidown"


def _show_startup_error(message: str) -> None:
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(0, message, "Bilidown startup error", 0x10)
        return
    if sys.platform == "darwin":
        escaped = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        script = f'display alert "Bilidown startup error" message "{escaped}" as critical'
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=10)
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    print(message, file=sys.stderr)


def _report_startup_error() -> None:
    details = traceback.format_exc()
    base = _diagnostic_directory()
    try:
        base.mkdir(parents=True, exist_ok=True)
        log_path = base / "startup-error.log"
        log_path.write_text(details, encoding="utf-8")
        message = f"Bilidown failed to start. Details were written to:\n{log_path}"
    except OSError:
        message = "Bilidown failed to start and could not write its diagnostic log."
    _show_startup_error(message)


if __name__ == "__main__":
    try:
        from bilidown.launcher import main

        main()
    except Exception:
        _report_startup_error()
        raise
