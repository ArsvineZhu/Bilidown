import importlib.util
from pathlib import Path

import pytest

import bilidown.app as app_module


def load_entrypoint():
    path = Path(__file__).parents[1] / "packaging" / "entrypoint.py"
    spec = importlib.util.spec_from_file_location("bilidown_packaging_entrypoint", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_open_output_directory_uses_macos_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(app_module.os, "name", "posix")
    monkeypatch.setattr(app_module.sys, "platform", "darwin")
    monkeypatch.setattr(
        app_module.subprocess,
        "Popen",
        lambda command, **_: captured.append(command),
    )

    app_module.open_output_directory(tmp_path)

    assert captured == [["open", str(tmp_path)]]


def test_open_output_directory_rejects_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_module.os, "name", "posix")
    monkeypatch.setattr(app_module.sys, "platform", "linux")

    with pytest.raises(NotImplementedError):
        app_module.open_output_directory(tmp_path)


def test_macos_startup_error_uses_logs_and_native_alert(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    entrypoint = load_entrypoint()
    commands: list[list[str]] = []
    monkeypatch.setattr(entrypoint.sys, "platform", "darwin")
    monkeypatch.setattr(entrypoint.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(
        entrypoint.subprocess,
        "run",
        lambda command, **_: commands.append(command),
    )

    assert entrypoint._diagnostic_directory() == tmp_path / "Library" / "Logs" / "Bilidown"
    entrypoint._show_startup_error("See log\npath")

    assert commands[0][:2] == ["osascript", "-e"]
    assert "See log\\npath" in commands[0][2]
