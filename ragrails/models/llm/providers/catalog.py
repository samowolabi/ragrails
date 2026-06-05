from ..types import ModelInfo


OPENAI_MODELS: list[ModelInfo] = [
    ModelInfo("gpt-5.5",             "openai", "latest flagship reasoning model",            5.00, 30.00, supports_tools=True),
    ModelInfo("gpt-5.5-pro",         "openai", "high-compute GPT-5.5",                      30.00, 180.00, supports_tools=True),
    ModelInfo("gpt-5.4",             "openai", "frontier reasoning model",                   2.50, 15.00, supports_tools=True),
    ModelInfo("gpt-5.4-mini",        "openai", "cost-efficient GPT-5.4",                     0.75, 4.50, supports_tools=True),
    ModelInfo("gpt-5.4-nano",        "openai", "lowest-cost GPT-5.4",                        0.20, 1.25, supports_tools=True),
    ModelInfo("gpt-5.4-pro",         "openai", "high-compute GPT-5.4",                      30.00, 180.00, supports_tools=True),
    ModelInfo("chat-latest",         "openai", "ChatGPT latest model alias",                 5.00, 30.00, supports_tools=True),
    ModelInfo("gpt-5.3-codex",       "openai", "coding-specialized GPT-5.3",                 1.75, 14.00, supports_tools=True),
    ModelInfo("gpt-5.2",             "openai", "previous GPT-5 flagship",                    1.75, 14.00, supports_tools=True),
    ModelInfo("gpt-5.2-chat-latest", "openai", "previous GPT-5.2 chat alias",                1.75, 14.00, supports_tools=True),
    ModelInfo("gpt-5.2-pro",         "openai", "previous high-compute GPT-5.2",             21.00, 168.00, supports_tools=True),
    ModelInfo("gpt-5.1",             "openai", "previous GPT-5.1 flagship",                  1.25, 10.00, supports_tools=True),
    ModelInfo("gpt-5.1-chat-latest", "openai", "previous GPT-5.1 chat alias",                1.25, 10.00, supports_tools=True),
    ModelInfo("gpt-5",               "openai", "previous GPT-5 model",                       1.25, 10.00, supports_tools=True),
    ModelInfo("gpt-5-chat-latest",   "openai", "previous GPT-5 chat alias",                  1.25, 10.00, supports_tools=True),
    ModelInfo("gpt-5-mini",          "openai", "previous cost-efficient GPT-5",              0.25, 2.00, supports_tools=True),
    ModelInfo("gpt-5-nano",          "openai", "previous lowest-cost GPT-5",                 0.05, 0.40, supports_tools=True),
    ModelInfo("gpt-5-pro",           "openai", "previous high-compute GPT-5",               15.00, 120.00, supports_tools=True),
    ModelInfo("gpt-4.1",             "openai", "strong non-reasoning model",                 2.00, 8.00, supports_tools=True),
    ModelInfo("gpt-4.1-mini",        "openai", "fast GPT-4.1",                               0.40, 1.60, supports_tools=True),
    ModelInfo("gpt-4.1-nano",        "openai", "lowest-cost GPT-4.1",                        0.10, 0.40, supports_tools=True),
    ModelInfo("gpt-4o",              "openai", "older multimodal chat model",                2.50, 10.00, supports_tools=True),
    ModelInfo("gpt-4o-mini",         "openai", "older low-cost multimodal chat model",       0.15, 0.60, supports_tools=True),
    ModelInfo("gpt-4-turbo",         "openai", "legacy GPT-4 model",                        10.00, 30.00, supports_tools=True),
    ModelInfo("o3",                  "openai", "legacy reasoning model",                     2.00, 8.00, supports_tools=False),
    ModelInfo("o4-mini",             "openai", "legacy cost-efficient reasoning model",      1.10, 4.40, supports_tools=False),
    ModelInfo("o1",                  "openai", "legacy full reasoning model",               15.00, 60.00, supports_tools=False),
    ModelInfo("o1-mini",             "openai", "legacy small reasoning model",               1.10, 4.40, supports_tools=False),
]


ANTHROPIC_MODELS: list[ModelInfo] = [
    ModelInfo("claude-opus-4-8",            "anthropic", "latest most capable Claude",       5.00, 25.00, supports_tools=True),
    ModelInfo("claude-opus-4-7",            "anthropic", "previous Opus 4.7",                5.00, 25.00, supports_tools=True),
    ModelInfo("claude-opus-4-6",            "anthropic", "previous Opus 4.6",                5.00, 25.00, supports_tools=True),
    ModelInfo("claude-opus-4-5",            "anthropic", "previous Opus 4.5",                5.00, 25.00, supports_tools=True),
    ModelInfo("claude-opus-4-1-20250805",   "anthropic", "older high-cost Opus 4.1",        15.00, 75.00, supports_tools=True),
    ModelInfo("claude-opus-4-20250514",     "anthropic", "deprecated Opus 4",               15.00, 75.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-6",          "anthropic", "latest balanced Claude",           3.00, 15.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-5",          "anthropic", "previous Sonnet 4.5 alias",        3.00, 15.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-5-20250929", "anthropic", "previous Sonnet 4.5 snapshot",     3.00, 15.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-20250514",   "anthropic", "deprecated Sonnet 4",              3.00, 15.00, supports_tools=True),
    ModelInfo("claude-haiku-4-5",           "anthropic", "fast cost-efficient Claude",       1.00, 5.00, supports_tools=True),
    ModelInfo("claude-haiku-4-5-20251001",  "anthropic", "fast Claude 4.5 snapshot",         1.00, 5.00, supports_tools=True),
    ModelInfo("claude-3-7-sonnet-20250219", "anthropic", "legacy Claude 3.7 Sonnet",         3.00, 15.00, supports_tools=True),
    ModelInfo("claude-3-5-sonnet-20241022", "anthropic", "legacy Claude 3.5 Sonnet",         3.00, 15.00, supports_tools=True),
    ModelInfo("claude-3-5-haiku-20241022",  "anthropic", "retired Claude 3.5 Haiku",         0.80, 4.00, supports_tools=True),
]


GOOGLE_MODELS: list[ModelInfo] = [
    ModelInfo("gemini-3-pro",             "google", "latest Gemini 3 Pro",                  2.00, 12.00, supports_tools=False),
    ModelInfo("gemini-3-pro-preview",     "google", "Gemini 3 Pro preview alias",          2.00, 12.00, supports_tools=False),
    ModelInfo("gemini-2.5-pro",           "google", "Gemini 2.5 Pro",                      1.25, 10.00, supports_tools=False),
    ModelInfo("gemini-2.5-flash",         "google", "fast cost-efficient Gemini 2.5",      0.30, 2.50, supports_tools=False),
    ModelInfo("gemini-2.5-flash-lite",    "google", "lowest-cost Gemini 2.5",              0.10, 0.40, supports_tools=False),
    ModelInfo("gemini-2.0-flash",         "google", "legacy fast Gemini 2.0",              0.10, 0.40, supports_tools=False),
    ModelInfo("gemini-2.0-flash-lite",    "google", "legacy lowest-cost Gemini 2.0",       0.075, 0.30, supports_tools=False),
]


MODELS = OPENAI_MODELS + ANTHROPIC_MODELS + GOOGLE_MODELS
