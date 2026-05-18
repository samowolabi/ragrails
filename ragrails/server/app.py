"""Compatibility wrapper for the Ragrails REST API server."""

from ragrails.usage.server.app import app, create_app, main

__all__ = ["app", "create_app", "main"]
