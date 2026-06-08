"""crawl4ai-backed URL ingestor.

mode="each"  — scrape exactly the URLs provided, one page per URL.
mode="full"  — BFS-crawl each URL's entire site sequentially, completing
               one before starting the next.

Parallel fetching within each BFS level is handled automatically by
crawl4ai. Results are returned in memory.
"""

import asyncio
import hashlib
import re
import time
from typing import Callable, Literal
from urllib.parse import urlparse, urlunparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import DomainFilter, FilterChain, URLPatternFilter

from ..config import UrlIngestorConfig


_SCROLL_JS = """
    await new Promise(resolve => {
        let timer = setInterval(() => {
            window.scrollBy(0, 300);
            if (window.scrollY + window.innerHeight >= document.body.scrollHeight) {
                clearInterval(timer); resolve();
            }
        }, 200);
        setTimeout(() => { clearInterval(timer); resolve(); }, 3000);
    });
"""

_BROWSER_CONFIG = BrowserConfig(headless=True, verbose=False)

_BASE_CONFIG = dict(
    js_code=_SCROLL_JS,
    wait_until="domcontentloaded",
    delay_before_return_html=2.0,
    page_timeout=30000,
    simulate_user=True,
    override_navigator=True,
    magic=True,
    cache_mode=CacheMode.BYPASS,
    excluded_tags=["nav", "footer", "aside", "header"],
    exclude_social_media_links=True,
)


def _slug(url: str) -> str:
    return re.sub(r"[^\w]", "_", urlparse(url).path.strip("/")) or "index"


def _strip_tracking_pixels(markdown: str) -> str:
    """Remove markdown image tags with empty alt text — always tracking pixels, never content."""
    return re.sub(r"!\[\]\([^)]+\)", "", markdown)


def _strip_link_heavy_blocks(markdown: str, threshold: float = 0.6) -> str:
    """Strip leading paragraphs that are predominantly links (nav/footer leakage)."""
    blocks = re.split(r"\n{2,}", markdown)
    leading_done = False
    kept = []
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        if not leading_done:
            link_total = sum(len(m) for m in re.findall(r"\[[^\]]+\]\([^)]+\)", stripped))
            if link_total / len(stripped) > threshold:
                continue
            leading_done = True
        kept.append(block)
    return "\n\n".join(kept)


def _browser_setup_error(error: Exception) -> str:
    """Return a user-actionable Playwright browser setup error."""
    message = str(error)
    if "playwright install" not in message and "Executable doesn't exist" not in message:
        return f"Browser setup failed: {message}"

    return (
        "Browser setup failed: Playwright browser binaries are missing. "
        "Run this once in the same Python environment that runs Ragrails:\n"
        "    from ragrails import RagRails\n"
        "    RagRails().setup_url()\n"
        "Or run manually:\n"
        "    python -m playwright install chromium\n"
        f"Original error: {message}"
    )


def _crawler_run_options(verbose: bool) -> dict:
    return {**_BASE_CONFIG, "verbose": verbose, "log_console": False}


def _error(
    source: str,
    error: str,
    stage: str,
    *,
    source_kind: str = "url",
    mode: Literal["each", "full"] | None = None,
    root_url: str | None = None,
    attempts: int | None = None,
    is_retryable: bool = False,
    retry_input: dict | None = None,
) -> dict:
    payload = {
        "source": source,
        "source_kind": source_kind,
        "error": error,
        "stage": stage,
        "isRetryable": is_retryable,
    }
    if mode:
        payload["mode"] = mode
    if root_url:
        payload["root_url"] = root_url
    if attempts is not None:
        payload["attempts"] = attempts
    if retry_input:
        payload["retry_input"] = retry_input
    return payload


def _retry_input(
    url: str,
    *,
    mode: Literal["each", "full"] = "each",
    max_depth: int = 1,
    max_pages: int = 1,
) -> dict:
    return {
        "url": url,
        "mode": mode,
        "max_depth": max_depth,
        "max_pages": max_pages,
    }


def _crawled_page(source: str, document_id: str) -> dict:
    return {"source": source, "id": document_id}


def _emit_progress(callback: Callable[[dict], None] | None, event: dict) -> None:
    if callback is not None:
        callback(event)


def _document_id(source: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}\n{text}".encode("utf-8")).hexdigest()[:16]
    return f"url_{digest}"


def _normalize_url_inputs(
    urls: str | list[str | dict],
    *,
    default_mode: Literal["each", "full"],
    default_config: UrlIngestorConfig,
) -> tuple[list[dict], list[dict]]:
    items = [urls] if isinstance(urls, str) else list(urls or [])
    requests = []
    errors = []
    seen = set()

    for item in items:
        try:
            request = _normalize_url_input(
                item,
                default_mode=default_mode,
                default_config=default_config,
            )
            request_key = _request_key(request)
            if request_key in seen:
                continue
            seen.add(request_key)
            requests.append(request)
        except Exception as e:
            source = item.get("url") or item.get("path") if isinstance(item, dict) else str(item)
            errors.append(_error(source=source, error=str(e), stage="validate", is_retryable=False))

    return requests, errors


def _request_key(request: dict) -> tuple[str, str, int, int]:
    parsed = urlparse(request["url"])
    normalized_path = parsed.path.rstrip("/")
    normalized_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        normalized_path,
        "",
        parsed.query,
        "",
    ))
    return (
        normalized_url,
        request["mode"],
        request["max_depth"],
        request["max_pages"],
    )


def _normalize_url_input(
    item: str | dict,
    *,
    default_mode: Literal["each", "full"],
    default_config: UrlIngestorConfig,
) -> dict:
    if isinstance(item, str):
        url = item
        mode = default_mode
        max_depth = default_config.max_depth
        max_pages = default_config.max_pages
    elif isinstance(item, dict):
        url = item.get("url") or item.get("path")
        mode = item.get("mode", default_mode)
        item_config = item.get("config")
        if isinstance(item_config, UrlIngestorConfig):
            max_depth = item.get("max_depth", item_config.max_depth)
            max_pages = item.get("max_pages", item_config.max_pages)
        elif isinstance(item_config, dict):
            max_depth = item.get("max_depth", item_config.get("max_depth", default_config.max_depth))
            max_pages = item.get("max_pages", item_config.get("max_pages", default_config.max_pages))
        else:
            max_depth = item.get("max_depth", default_config.max_depth)
            max_pages = item.get("max_pages", default_config.max_pages)
    else:
        raise TypeError("URL entries must be strings or dictionaries")

    normalized_url = _normalize_url(url)
    if mode not in {"each", "full"}:
        raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")

    return {
        "url": normalized_url,
        "mode": mode,
        "max_depth": _validate_positive_int(max_depth, "max_depth"),
        "max_pages": _validate_positive_int(max_pages, "max_pages"),
    }


def _normalize_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("url must include a host")

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path or "",
        "",
        parsed.query,
        "",
    ))


def _validate_positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _render_document(
    content: str,
    url: str,
    index: int,
    mode: Literal["each", "full"],
    max_depth: int,
    max_pages: int,
    elapsed_seconds: float,
    status_code: int = 200,
    meta: dict = None,
) -> tuple[dict, float]:
    body = _strip_link_heavy_blocks(_strip_tracking_pixels(str(content)))
    size_kb = len(body.encode()) / 1024
    return {
        "id": _document_id(url, body),
        "display_id": f"{index:03d}_{_slug(url)}",
        "source": url,
        "title": (meta or {}).get("title", ""),
        "text": body,
        "metadata": {
            "url": url,
            "status_code": status_code,
            "file_type": "web",
            "source_kind": "url",
            "mode": mode,
            "max_depth": max_depth,
            "max_pages": max_pages,
            "elapsed_seconds": elapsed_seconds,
            "size_bytes": len(body.encode()),
        },
    }, size_kb


async def _crawl_one(
    crawler: AsyncWebCrawler,
    url: str,
    index: int,
    max_depth: int,
    max_pages: int,
    verbose: bool,
    progress_callback: Callable[[dict], None] | None = None,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> dict:
    """Scrape a single URL and return its markdown. Retries on transient errors."""
    config = CrawlerRunConfig(**_crawler_run_options(verbose))
    last_error = ""
    last_stage = "crawl"

    for attempt in range(1, max_retries + 1):
        _emit_progress(progress_callback, {
            "type": "progress",
            "stage": "scrape",
            "message": "Started URL scrape",
            "data": {"url": url, "mode": "each", "attempt": attempt},
        })
        start = time.time()
        result = await crawler.arun(url=url, config=config)
        elapsed = time.time() - start

        if result.success:
            document, size_kb = _render_document(
                result.markdown,
                url,
                index,
                "each",
                max_depth,
                max_pages,
                elapsed,
                result.status_code,
                result.metadata,
            )
            if not document["text"].strip():
                last_error = "no content returned after cleanup"
                last_stage = "cleanup"
                break
            _emit_progress(progress_callback, {
                "type": "page",
                "stage": "scrape",
                "message": "Scraped page",
                "data": {
                    "url": url,
                    "document_id": document["id"],
                    "status_code": result.status_code,
                    "size_kb": size_kb,
                    "elapsed_seconds": elapsed,
                },
            })
            return {
                "pages": 1,
                "failed": 0,
                "total_kb": size_kb,
                "page_times": [(url, elapsed, size_kb)],
                "outputs": [document],
                "crawled": [_crawled_page(url, document["id"])],
            }

        last_error = result.error_message or "unknown error"
        last_stage = "crawl"
        _emit_progress(progress_callback, {
            "type": "error",
            "stage": "scrape",
            "message": last_error,
            "data": {"url": url, "mode": "each", "attempt": attempt},
        })
        if attempt < max_retries:
            delay = retry_delay * attempt
            await asyncio.sleep(delay)

    return {
        "pages": 0,
        "failed": 1,
        "total_kb": 0.0,
        "errors": [_error(
            source=url,
            error=last_error,
            stage=last_stage,
            mode="each",
            attempts=max_retries,
            is_retryable=last_stage == "crawl",
            retry_input=_retry_input(url, max_depth=max_depth, max_pages=max_pages) if last_stage == "crawl" else None,
        )],
    }


async def _crawl_site(
    crawler: AsyncWebCrawler,
    url: str,
    max_depth: int,
    max_pages: int,
    verbose: bool,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """BFS-crawl an entire site and return markdown documents."""
    domain = urlparse(url).netloc
    config = CrawlerRunConfig(
        **_crawler_run_options(verbose),
        stream=True,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            filter_chain=FilterChain([
                DomainFilter(allowed_domains=[domain]),
                URLPatternFilter(patterns=[
                    r".*\.(zip|pdf|exe|dmg|pkg|tar|gz|rar|7z|mp4|mp3|avi|"
                    r"mov|wmv|flv|woff|woff2|ttf|eot|otf|ico|png|jpg|jpeg|"
                    r"gif|svg|webp|css|js|xml|json|csv|xlsx|docx|pptx)$"
                ], reverse=True),
            ]),
        ),
    )

    pages, failed, total_kb, page_times = 0, 0, 0.0, []
    outputs = []
    errors = []
    crawled: list[dict] = []
    seen: set[str] = set()
    last_yield_at = time.time()

    try:
        _emit_progress(progress_callback, {
            "type": "progress",
            "stage": "scrape",
            "message": "Started site crawl",
            "data": {"url": url, "mode": "full", "max_depth": max_depth, "max_pages": max_pages},
        })
        stream = await crawler.arun(url=url, config=config)
    except Exception as e:
        return {
            "pages": 0,
            "failed": 1,
            "total_kb": 0.0,
            "page_times": [],
            "outputs": [],
            "crawled": [],
            "errors": [_error(
                source=url,
                error=str(e),
                stage="crawl",
                mode="full",
                root_url=url,
                attempts=1,
                is_retryable=True,
                retry_input=_retry_input(url, mode="full", max_depth=max_depth, max_pages=max_pages),
            )],
        }

    async for result in stream:
        yielded_at = time.time()
        fallback_elapsed = yielded_at - last_yield_at
        last_yield_at = yielded_at

        if not result.success or not result.markdown:
            failed += 1
            error = _error(
                source=result.url,
                error=result.error_message or "no markdown returned",
                stage="crawl",
                mode="full",
                root_url=url,
                attempts=1,
                is_retryable=True,
                retry_input=_retry_input(result.url),
            )
            errors.append(error)
            _emit_progress(progress_callback, {
                "type": "error",
                "stage": "scrape",
                "message": error["error"],
                "data": error,
            })
            continue

        normalized = result.url.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)

        display_index = pages + 1
        page_time = result.metadata.get("timing", {}).get("total", 0.0) if result.metadata else 0.0
        if not page_time:
            page_time = fallback_elapsed
        document, size_kb = _render_document(
            result.markdown,
            result.url,
            display_index,
            "full",
            max_depth,
            max_pages,
            page_time,
            result.status_code,
            result.metadata,
        )
        if not document["text"].strip():
            failed += 1
            error = _error(
                source=result.url,
                error="no content returned after cleanup",
                stage="cleanup",
                mode="full",
                root_url=url,
                attempts=1,
                is_retryable=False,
            )
            errors.append(error)
            _emit_progress(progress_callback, {
                "type": "error",
                "stage": "scrape",
                "message": error["error"],
                "data": error,
            })
            continue

        pages += 1
        outputs.append(document)
        crawled.append(_crawled_page(result.url, document["id"]))
        total_kb += size_kb
        page_times.append((result.url, page_time, size_kb))
        _emit_progress(progress_callback, {
            "type": "page",
            "stage": "scrape",
            "message": "Crawled page",
            "data": {
                "url": result.url,
                "document_id": document["id"],
                "status_code": result.status_code,
                "size_kb": size_kb,
                "elapsed_seconds": page_time,
                "pages": pages,
            },
        })

    return {"pages": pages, "failed": failed, "total_kb": total_kb, "page_times": page_times, "outputs": outputs, "crawled": crawled, "errors": errors}


async def scrape_url(
    urls: str | list[str | dict],
    mode: Literal["each", "full"] = "each",
    config: UrlIngestorConfig | None = None,
    verbose: bool = True,
    progress_callback: Callable[[dict], None] | None = None,
    **_ignored_options,
) -> dict:
    """Scrape URL entries and return successful documents plus failed pages."""
    cfg = config or UrlIngestorConfig()
    requests, input_errors = _normalize_url_inputs(urls, default_mode=mode, default_config=cfg)

    totals = {"pages": 0, "failed": 0, "total_kb": 0.0, "page_times": [], "outputs": [], "crawled": [], "errors": []}
    totals["failed"] += len(input_errors)
    totals["errors"].extend(input_errors)
    if not requests:
        return totals

    try:
        async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
            for i, request in enumerate(requests, start=1):
                if request["mode"] == "each":
                    stats = await _crawl_one(
                        crawler,
                        request["url"],
                        index=i,
                        max_depth=request["max_depth"],
                        max_pages=request["max_pages"],
                        verbose=verbose,
                        progress_callback=progress_callback,
                    )
                elif request["mode"] == "full":
                    stats = await _crawl_site(
                        crawler,
                        request["url"],
                        request["max_depth"],
                        request["max_pages"],
                        verbose=verbose,
                        progress_callback=progress_callback,
                    )
                else:
                    raise ValueError(f"Invalid mode '{request['mode']}' — use 'each' or 'full'")

                totals["pages"] += stats["pages"]
                totals["failed"] += stats["failed"]
                totals["total_kb"] += stats["total_kb"]
                totals["page_times"].extend(stats.get("page_times", []))
                totals["outputs"].extend(stats.get("outputs", []))
                totals["crawled"].extend(stats.get("crawled", []))
                totals["errors"].extend(stats.get("errors", []))
    except Exception as e:
        message = _browser_setup_error(e)
        totals["failed"] += len(requests)
        totals["errors"].append(_error(source="browser", error=message, stage="setup", is_retryable=False))

    return totals
