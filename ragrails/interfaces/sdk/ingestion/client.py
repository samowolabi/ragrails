"""SDK ingestion mixin — composes docs, url, and api ingestion."""

from .docs.client import DocsMixin
from .url.client import UrlMixin
from .api.client import ApiMixin


class IngestionMixin(DocsMixin, UrlMixin, ApiMixin):
    pass
