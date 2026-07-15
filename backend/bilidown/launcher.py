from __future__ import annotations

import os
import secrets
import socket
import threading
import time
import webbrowser

import uvicorn

from .app import create_app


def _find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _configured_port() -> int:
    value = os.getenv("BILIDOWN_PORT")
    if value is None:
        return _find_available_port()
    try:
        port = int(value)
    except ValueError as exc:
        raise ValueError("BILIDOWN_PORT must be an integer from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("BILIDOWN_PORT must be an integer from 1 to 65535")
    return port


def _open_when_ready(url: str, port: int) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.1)


def main() -> None:
    port = _configured_port()
    token = os.getenv("BILIDOWN_SESSION_TOKEN") or secrets.token_urlsafe(32)
    origin = f"http://127.0.0.1:{port}"
    server: uvicorn.Server

    def request_shutdown() -> None:
        server.should_exit = True

    app = create_app(
        session_token=token,
        expected_origin=origin,
        shutdown_callback=request_shutdown,
    )
    if os.getenv("BILIDOWN_NO_BROWSER") != "1":
        threading.Thread(
            target=_open_when_ready,
            args=(f"{origin}/?token={token}", port),
            daemon=True,
        ).start()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
        )
    )
    server.run()


if __name__ == "__main__":
    main()
