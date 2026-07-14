from pathlib import Path

from fastapi.testclient import TestClient

from bilidown.app import create_app
from bilidown.models import AuthStatus


TOKEN = "test-token"
ORIGIN = "http://127.0.0.1:9999"
HEADERS = {"X-Bilidown-Token": TOKEN, "Origin": ORIGIN}


def test_api_rejects_missing_token(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    with TestClient(app) as client:
        response = client.get("/api/status", headers={"Origin": ORIGIN})
    assert response.status_code == 401


def test_api_rejects_wrong_origin(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    with TestClient(app) as client:
        response = client.get(
            "/api/status",
            headers={"X-Bilidown-Token": TOKEN, "Origin": "http://evil.example"},
        )
    assert response.status_code == 403


def test_status_and_cookie_session_lifecycle(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    cookie_data = (
        "# Netscape HTTP Cookie File\n"
        ".bilibili.com\tTRUE\t/\tTRUE\t0\tSESSDATA\tsecret\n"
    )
    with TestClient(app) as client:
        status = client.get("/api/status", headers=HEADERS)
        assert status.status_code == 200
        assert "yt_dlp_version" in status.json()

        created = client.post(
            "/api/auth/cookie-sessions",
            files={"file": ("cookies.txt", cookie_data, "text/plain")},
            headers=HEADERS,
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]
        deleted = client.delete(f"/api/auth/cookie-sessions/{session_id}", headers=HEADERS)
        assert deleted.status_code == 204


def test_same_origin_referer_allows_get_without_origin(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    with TestClient(app) as client:
        response = client.get(
            "/api/status",
            headers={"X-Bilidown-Token": TOKEN, "Referer": f"{ORIGIN}/"},
        )
    assert response.status_code == 200
    assert response.headers["referrer-policy"] == "same-origin"


def test_csp_is_present_on_frontend(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_auth_status_endpoint_returns_safe_account_summary(tmp_path: Path) -> None:
    app = create_app(session_token=TOKEN, expected_origin=ORIGIN, static_dir=tmp_path / "missing")
    app.state.engine.auth_status = lambda _: AuthStatus(
        state="active",
        username="测试用户",
        vip_active=True,
        vip_label="年度大会员",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/status",
            json={"auth": {"kind": "browser", "browser": "edge"}},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == {
        "state": "active",
        "username": "测试用户",
        "vip_active": True,
        "vip_label": "年度大会员",
    }
    assert "SESSDATA" not in response.text
