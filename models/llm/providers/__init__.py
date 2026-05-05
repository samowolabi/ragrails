from . import anthropic, openai

PROVIDERS = {
    openai.PROVIDER: openai,
    anthropic.PROVIDER: anthropic,
}

__all__ = ["PROVIDERS", "anthropic", "openai"]
