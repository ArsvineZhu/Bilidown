from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class LocalSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, token: str, expected_origin: str) -> None:
        super().__init__(app)
        self.token = token
        self.expected_origin = expected_origin.rstrip("/")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api/"):
            supplied = request.headers.get("x-bilidown-token", "")
            if not hmac.compare_digest(supplied, self.token):
                return JSONResponse({"detail": "无效的本地会话令牌"}, status_code=401)

            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            origin_valid = origin == self.expected_origin
            referer_valid = bool(referer) and referer.startswith(f"{self.expected_origin}/")
            if not origin_valid and not referer_valid:
                return JSONResponse({"detail": "请求来源不受信任"}, status_code=403)

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: blob: https://*.hdslb.com https://*.bilibili.com; "
            "connect-src 'self'; font-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response
