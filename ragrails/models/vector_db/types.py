from dataclasses import dataclass


@dataclass(frozen=True)
class VectorStoreInfo:
    provider: str
    default_url: str
    default_collection: str
