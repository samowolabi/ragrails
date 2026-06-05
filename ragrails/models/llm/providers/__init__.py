from importlib import import_module

PROVIDER_MODULES = {
    "openai": "ragrails.models.llm.providers.openai",
    "anthropic": "ragrails.models.llm.providers.anthropic",
    "google": "ragrails.models.llm.providers.google",
}


class _ProviderMap:
    def __contains__(self, provider: str) -> bool:
        return provider in PROVIDER_MODULES

    def __getitem__(self, provider: str):
        if provider not in PROVIDER_MODULES:
            raise KeyError(provider)
        return import_module(PROVIDER_MODULES[provider])

    def __iter__(self):
        return iter(PROVIDER_MODULES)

    def values(self):
        return [self[provider] for provider in PROVIDER_MODULES]


PROVIDERS = _ProviderMap()

__all__ = ["PROVIDERS", "PROVIDER_MODULES"]
