import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("nexly.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request id + latency log + security headers. يسجّل المسار فقط (بدون query string) حتى لا
    تتسرب قيم بحث أو معرفات حساسة إلى الـ logs."""

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.error("unhandled", extra={"request_id": request_id, "method": request.method,
                         "path": request.url.path, "status": 500, "error_category": "unhandled_exception"})
            raise
        latency = int((time.monotonic() - start) * 1000)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "same-origin"
        category = "server_error" if response.status_code >= 500 else "client_error" if response.status_code >= 400 else None
        extra = {"request_id": request_id, "method": request.method, "path": request.url.path,
                 "status": response.status_code, "latency_ms": latency}
        if category:
            extra["error_category"] = category
        logger.info("request", extra=extra)
        return response
