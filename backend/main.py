"""Proofline AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.routers import guidelines, audit, adapt, approve, consistency, steps, config

MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024  # 2 MB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    logging.getLogger(__name__).info("Proofline AI backend started")
    yield


app = FastAPI(
    title="Proofline AI",
    description="Content Risk & Approval Copilot — Every content change, backed by a rule.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    """Reject requests larger than MAX_REQUEST_BODY_BYTES to prevent abuse."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(status_code=413, content={"error": f"Request body too large (max {MAX_REQUEST_BODY_BYTES // 1024}KB)"})
    return await call_next(request)


app.include_router(guidelines.router)
app.include_router(audit.router)
app.include_router(adapt.router)
app.include_router(approve.router)
app.include_router(consistency.router)
app.include_router(steps.router)
app.include_router(config.router)


# ── Global exception handler — catches LLM 429/500 and other unhandled errors ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return clean JSON instead of stack traces."""
    error_type = type(exc).__name__
    # Check for common LLM/API errors
    if "rate" in str(exc).lower() or "429" in str(exc):
        logger.warning("Rate limit hit: %s", exc)
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded. Please wait and retry.", "type": error_type})
    if "timeout" in str(exc).lower():
        logger.warning("Timeout: %s", exc)
        return JSONResponse(status_code=504, content={"error": "Request timed out. Please retry.", "type": error_type})
    logger.error("Unhandled exception: %s: %s", error_type, exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error. Please retry.", "type": error_type})


@app.get("/health")
def health():
    return {"status": "ok", "service": "proofline-ai"}
