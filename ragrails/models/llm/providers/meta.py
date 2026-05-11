from ..types import ModelInfo


OPENAI_MODELS: list[ModelInfo] = [
    ModelInfo("gpt-4o-mini", "openai", "fast & cheap    — generation, rewriting, summarization", 0.15, 0.60, supports_tools=True),
    ModelInfo("gpt-4o",      "openai", "capable         — tool calling, complex tasks",          2.50, 10.00, supports_tools=True),
    ModelInfo("gpt-4-turbo", "openai", "capable         — alternative to gpt-4o",                10.00, 30.00, supports_tools=True),
    ModelInfo("o1-mini",     "openai", "reasoning       — complex multi-step problems",           3.00, 12.00, supports_tools=False),
    ModelInfo("o1",          "openai", "full reasoning  — strongest reasoning model",            15.00, 60.00, supports_tools=False),
]


ANTHROPIC_MODELS: list[ModelInfo] = [
    ModelInfo("claude-haiku-4-5-20251001", "anthropic", "fast & cheap    — lightweight tasks",    0.80, 4.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-6",         "anthropic", "capable         — balanced performance", 3.00, 15.00, supports_tools=True),
    ModelInfo("claude-opus-4-7",           "anthropic", "most capable    — complex reasoning",   15.00, 75.00, supports_tools=True),
]


MODELS = OPENAI_MODELS + ANTHROPIC_MODELS
