from __future__ import annotations

import os

import uvicorn

from .app import create_app


def main() -> None:
    token = os.getenv("BILIDOWN_DEV_TOKEN", "dev-token")
    origin = os.getenv("BILIDOWN_DEV_ORIGIN", "http://127.0.0.1:5173")
    server: uvicorn.Server

    def request_shutdown() -> None:
        server.should_exit = True

    app = create_app(
        session_token=token,
        expected_origin=origin,
        shutdown_callback=request_shutdown,
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="info"))
    server.run()


if __name__ == "__main__":
    main()
