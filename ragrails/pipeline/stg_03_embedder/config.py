from dataclasses import dataclass


@dataclass
class EmbedderConfig:
    batch_size: int = 64
    input_type: str = "document"
    input_dir: str = "files/output/chunks"
