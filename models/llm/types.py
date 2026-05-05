"""Shared LLM registry types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Identity, pricing, and capability metadata for a registered model.

    Example:
        ModelInfo("gpt-4o", "openai", "capable — tool calling", 2.50, 10.00, supports_tools=True)
    """
    name:           str
    provider:       str
    description:    str
    input_price:    float  # USD per 1M input tokens
    output_price:   float  # USD per 1M output tokens
    supports_tools: bool = True
