import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bottleiq.config import settings
from bottleiq.db import SessionLocal
from bottleiq.migrations import check_migrations
from bottleiq.routes import auth, catalog, imports, incoming, orders

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bottleiq")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings().environment != "test":
        check_migrations()
    yield


app = FastAPI(title="BottleIQ API", version="0.1.0", lifespan=lifespan)


class BodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        messages: list[Message] = []
        size = 0
        while True:
            message = await receive()
            size += len(message.get("body", b""))
            if size > settings().max_upload_bytes + 1024 * 1024:
                await JSONResponse({"detail": "Request exceeds upload limit"}, 413)(
                    scope, receive, send
                )
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def bounded_receive() -> Message:
            return messages.pop(0) if messages else await receive()

        await self.app(scope, bounded_receive, send)


app.add_middleware(BodyLimit)
attempts: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_context(request: Request, call_next: object) -> object:
    request_id = str(uuid4())
    started = time.monotonic()
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != settings().web_origin:
            return JSONResponse({"detail": "Request origin is not allowed"}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site mutations are not allowed"}, 403)
    if (
        request.url.path in ("/auth/login", "/auth/signup", "/auth/demo")
        and request.method == "POST"
    ):
        key = request.client.host if request.client else "unknown"
        bucket = attempts[key]
        while bucket and started - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 20:
            return JSONResponse(
                {"detail": "Too many sign-in attempts. Try again in a minute."},
                429,
                headers={"Retry-After": "60"},
            )
        bucket.append(started)
        if len(attempts) > 10000:
            for stale in list(attempts):
                if not attempts[stale] or started - attempts[stale][-1] > 60:
                    del attempts[stale]
    try:
        response = await call_next(request)  # type: ignore[operator]
    except Exception:
        logger.exception(json.dumps({"event": "request_failed", "request_id": request_id}))
        response = JSONResponse(
            {"detail": "An unexpected error occurred. Please retry.", "request_id": request_id}, 500
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return response


@app.get("/health", tags=["Operations"])
def health() -> JSONResponse:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "database": "connected"})
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable", "database": "unreachable"}, 503)


for router in (auth.router, catalog.router, imports.router, incoming.router, orders.router):
    app.include_router(router)
