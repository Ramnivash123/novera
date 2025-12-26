"""
Main FastAPI application entry point.
Configures routes, middleware, and application lifecycle events.
"""

from contextlib import asynccontextmanager
import sys
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.core.config import settings
from app.db.session import init_db, close_db

# Routers
from app.api.endpoints.health import router as health_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.documents import router as documents_router
from app.api.endpoints.document_editor import router as document_editor_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.search import router as search_router
from app.api.endpoints.admin import router as admin_router


# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
logger.remove()

logger.add(
    sys.stdout,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level=settings.log_level,
    colorize=True,
)

logger.add(
    settings.log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level,
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    compression="zip",
)


# -------------------------------------------------------------------
# Application lifespan
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Mentanova AI Knowledge Assistant...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        await init_db()
        logger.info("✅ Database initialized")
        logger.info("🎉 Application startup complete!")
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

    yield

    logger.info("🛑 Shutting down Mentanova AI Knowledge Assistant...")

    try:
        await close_db()
        logger.info("✅ Database connections closed")
        logger.info("👋 Shutdown complete")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")


# -------------------------------------------------------------------
# FastAPI application
# -------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered knowledge assistant with RAG capabilities for finance and HRMS documentation",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# -------------------------------------------------------------------
# Middleware
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# -------------------------------------------------------------------
# API Routers (VERSIONED)
# -------------------------------------------------------------------
API_PREFIX = settings.api_v1_prefix

app.include_router(health_router, prefix=API_PREFIX, tags=["Health"])
app.include_router(auth_router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(documents_router, prefix=API_PREFIX, tags=["Documents"])
app.include_router(search_router, prefix=API_PREFIX, tags=["Search"])
app.include_router(chat_router, prefix=API_PREFIX, tags=["Chat"])
app.include_router(document_editor_router, prefix=API_PREFIX, tags=["Document Editor"])
app.include_router(admin_router, prefix=API_PREFIX, tags=["Admin"])


# -------------------------------------------------------------------
# Frontend (Vite build)
# -------------------------------------------------------------------
FRONTEND_DIR = "backend/static"
INDEX_FILE = os.path.join(FRONTEND_DIR, "index.html")

if os.path.exists(FRONTEND_DIR):
    # Serve frontend + assets at ROOT
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )


# SPA fallback (React Router / Vue Router support)
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        return {"detail": "Not Found"}
    return FileResponse(INDEX_FILE)


# -------------------------------------------------------------------
# Global exception handler
# -------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "message": str(exc) if settings.debug else "An error occurred",
    }


# -------------------------------------------------------------------
# Local development entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower(),
    )
