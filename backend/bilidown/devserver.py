from __future__ import annotations

import os

import uvicorn

from .app import create_app


def main() -> None:
    token = os.getenv("BILIDOWN_DEV_TOKEN", "dev-token")
    origin = os.getenv("BILIDOWN_DEV_ORIGIN", "http://127.0.0.1:5173")
    app = create_app(session_token=token, expected_origin=origin)
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
