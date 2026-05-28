from dataclasses import dataclass


@dataclass
class UrlIngestorConfig:
    max_depth: int = 3
    max_pages: int = 200


@dataclass
class ApiIngestorConfig:
    max_pages: int = 100
    timeout: float = 30.0


@dataclass
class DocsIngestorConfig:
    pass


# Convenience alias when ingestor type is determined at call site
IngestorConfig = UrlIngestorConfig
