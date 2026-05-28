"""FastAPI application entrypoint for the Ragrails REST API."""

from __future__ import annotations

import argparse

from fastapi import FastAPI

from .errors import register_exception_handlers
from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ragrails API",
        description="Language-agnostic REST API for Ragrails ingestion, chunking, embedding, storage, and retrieval.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/v1/openapi.json",
    )
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Ragrails REST API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind.")
    parser.add_argument("--reload", action="store_true", help="Enable Uvicorn reload mode.")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("REST API server dependencies are missing. Reinstall with: pip install -U ragrails") from exc

    uvicorn.run(
        "ragrails.interfaces.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
