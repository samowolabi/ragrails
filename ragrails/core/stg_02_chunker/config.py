from dataclasses import dataclass


@dataclass
class ChunkerConfig:
    chunk_size: int = 2000      # ~512 tokens
    chunk_overlap: int = 200
    min_chunk_length: int = 100
