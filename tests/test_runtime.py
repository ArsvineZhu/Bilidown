from pathlib import Path

import bilidown.runtime as runtime


def test_application_root_uses_pyinstaller_meipass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert runtime.application_root() == tmp_path
