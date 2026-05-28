"""
URL ingestor — wraps scraper.scrape_url for direct use by other modules.
"""

from .scraper import scrape_url
from ..config import UrlIngestorConfig

__all__ = ["scrape_url", "UrlIngestorConfig"]
