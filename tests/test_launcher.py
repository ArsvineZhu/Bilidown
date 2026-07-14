import pytest

import bilidown.launcher as launcher


def test_configured_port_defaults_to_random_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BILIDOWN_PORT", raising=False)
    monkeypatch.setattr(launcher, "_find_available_port", lambda: 43210)

    assert launcher._configured_port() == 43210


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port", "1.5"])
def test_configured_port_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("BILIDOWN_PORT", value)

    with pytest.raises(ValueError, match="BILIDOWN_PORT"):
        launcher._configured_port()


def test_configured_port_accepts_explicit_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BILIDOWN_PORT", "49152")

    assert launcher._configured_port() == 49152
