"""HTTP error handling for the Ragrails REST API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _error_response(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }
        },
    )


async def validation_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return _error_response(400, exc)


async def not_found_error_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    return _error_response(404, exc)


async def bad_path_error_handler(request: Request, exc: OSError) -> JSONResponse:
    return _error_response(400, exc)


async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    return _error_response(500, exc)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValueError, validation_error_handler)
    app.add_exception_handler(FileNotFoundError, not_found_error_handler)
    app.add_exception_handler(NotADirectoryError, bad_path_error_handler)
    app.add_exception_handler(IsADirectoryError, bad_path_error_handler)
    app.add_exception_handler(RuntimeError, runtime_error_handler)
