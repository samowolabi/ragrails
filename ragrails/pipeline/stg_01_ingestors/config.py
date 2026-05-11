from dataclasses import dataclass, field


@dataclass
class UrlIngestorConfig:
    output_dir: str = "files/output/web_crawled"
    dlq_path: str = "files/output/dlq.json"
    max_depth: int = 3
    max_pages: int = 200
    rate_limit: float = 1.0
    allowed_domains: list[str] = field(default_factory=list)


@dataclass
class ApiIngestorConfig:
    output_dir: str = "files/output/api"
    max_pages: int = 100
    timeout: float = 30.0


@dataclass
class DocsIngestorConfig:
    input_dir: str = "files/input"
    output_dir: str = "files/output/docs"


# Convenience alias when ingestor type is determined at call site
IngestorConfig = UrlIngestorConfig
