from dataclasses import dataclass


@dataclass
class StoringConfig:
    batch_size: int = 64
    ensure_collection: bool = True
