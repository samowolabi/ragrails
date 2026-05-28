from dataclasses import dataclass


@dataclass
class EmbedderConfig:
    batch_size: int = 64
