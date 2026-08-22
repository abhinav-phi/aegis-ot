"""AEGIS-OT FastAPI application factory."""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import health_router, router as auth_router, users_router
from app.api.data import audit_router, demo_router, eval_router, router as data_router
from app.api.operations import router as ops_router
from app.core.exceptions import AegisError
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.db.immutability import register_immutability_listeners

log = get_logger("aegis.app")


def create_app() -> FastAPI:
    configure_logging()
    register_immutability_listeners()

    app = FastAPI(title="AEGIS-OT", version="1.0.0",
                  description="Research-grade OT decision support. "
                              "All actions simulated; no real plant connectivity (R1).")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed = int((time.perf_counter() - started) * 1000)
            log.info("http", extra={})
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Duration-Ms"] = str(elapsed)
        return response

    @app.exception_handler(AegisError)
    async def aegis_error_handler(_req: Request, exc: AegisError):
        return JSONResponse(status_code=exc.status_code,
                            content={"ok": False, "code": exc.code,
                                     "detail": str(exc), "details": exc.details})

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(health_router)
    app.include_router(data_router)
    app.include_router(eval_router)
    app.include_router(audit_router)
    app.include_router(demo_router)
    app.include_router(ops_router)

    return app


app = create_app()
