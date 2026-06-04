"""Versioned REST route aggregation for Ragrails."""

from __future__ import annotations

from fastapi import APIRouter

from . import chat, chunking, embedding, ingestion, pipeline, retrieval, storing
from .health import router as health_router

router = APIRouter()

router.include_router(health_router)
router.include_router(ingestion.router)
router.include_router(chunking.router)
router.include_router(embedding.router)
router.include_router(storing.router)
router.include_router(retrieval.router)
router.include_router(pipeline.router)
router.include_router(chat.router)
