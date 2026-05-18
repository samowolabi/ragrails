"""Versioned REST route aggregation for Ragrails."""

from __future__ import annotations

from fastapi import APIRouter

from . import chunking, embedding, ingestion, retrieval, storing
from .health import router as health_router

router = APIRouter()

router.include_router(health_router)
router.include_router(ingestion.router)
router.include_router(chunking.router)
router.include_router(embedding.router)
router.include_router(storing.router)
router.include_router(retrieval.router)
