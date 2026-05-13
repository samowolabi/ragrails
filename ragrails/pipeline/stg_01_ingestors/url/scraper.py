"""
crawl4ai-backed web scraper.

mode="each"  — scrape exactly the URLs provided, one page per URL.
mode="full"  — BFS-crawl each URL's entire site sequentially, completing
               one before starting the next.

Parallel fetching within each BFS level is handled automatically by
crawl4ai's MemoryAdaptiveDispatcher.
"""

import asyncio
import os
import re
import time
from typing import Literal
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import DomainFilter, FilterChain, URLPatternFilter

from ragrails.utils.resource_monitor import snapshot
from ragrails.utils.report import print_report
from ragrails.utils.frontmatter import build as build_frontmatter
from . import dlq as dlq_store
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


# ── helpers ──────────────────────────────────────────────────────────────────

def _reorder_by_url_tree(crawled: list[tuple[str, str]], output_dir: str) -> list[str]:
    """Rename files in order of URL path hierarchy.

    Args:
        crawled: list of (url, filename) collected during the crawl — already
                 in memory, no disk re-reads needed.
    """
    if not crawled:
        return []

    def sort_key(entry: tuple[str, str]):
        segments = urlparse(entry[0]).path.strip("/").split("/")
        return (len(segments), segments)

    sorted_entries = sorted(crawled, key=sort_key)

    final_files = []
    for i, (_, fname) in enumerate(sorted_entries, start=1):
        stem = re.sub(r"^\d+_", "", os.path.basename(fname))
        new_name = f"{i:03d}_{stem}"
        final_files.append(os.path.join(output_dir, new_name))
        if os.path.basename(fname) != new_name:
            os.rename(
                os.path.join(output_dir, os.path.basename(fname)),
                os.path.join(output_dir, f"_tmp_{new_name}"),
            )

    for fname in os.listdir(output_dir):
        if fname.startswith("_tmp_"):
            os.rename(
                os.path.join(output_dir, fname),
                os.path.join(output_dir, fname[5:]),
            )

    print(f"  Reordered {len(crawled)} files by URL tree in {output_dir}")
    return final_files


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


def _site_dir(base: str, url: str, many: bool) -> str:
    """Return output directory: subdirectory per domain when crawling many sites."""
    if not many:
        return base
    domain = re.sub(r"[^\w]", "_", urlparse(url).netloc)
    return os.path.join(base, domain)


def _frontmatter(url: str, status_code: int, meta: dict) -> str:
    return build_frontmatter(
        path=url,
        title=meta.get("title", ""),
        description=meta.get("description", ""),
        original_type="web",
        status_code=status_code,
    )


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


def _save(
    content: str,
    url: str,
    output_dir: str,
    index: int,
    status_code: int = 200,
    meta: dict = None,
    frontmatter: bool = True,
) -> tuple[str, float]:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{index:03d}_{_slug(url)}.md")
    # Step 1: Strip tracking pixels and link-heavy nav/footer blocks from markdown
    # Step 2: Optionally prepend frontmatter metadata
    # Step 3: Write cleaned markdown to disk
    body = _strip_link_heavy_blocks(_strip_tracking_pixels(str(content)))
    if frontmatter:
        body = _frontmatter(url, status_code, meta or {}) + body
    with open(filename, "w") as f:
        f.write(body)
    size_kb = len(body.encode()) / 1024
    return filename, size_kb


# ── single-page crawl ─────────────────────────────────────────────────────────

async def _crawl_one(
    crawler: AsyncWebCrawler,
    url: str,
    output_dir: str,
    index: int,
    dlq_path: str,
    frontmatter: bool,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> dict:
    """Scrape a single URL and save its markdown. Retries on transient errors."""
    # Step 1: Build crawler config (scroll JS, anti-bot options, cache bypass)
    config = CrawlerRunConfig(**_BASE_CONFIG)
    last_error = ""

    for attempt in range(1, max_retries + 1):
        # Step 2: Fetch the page; retry up to max_retries on transient failures
        start = time.time()
        result = await crawler.arun(url=url, config=config)
        elapsed = time.time() - start

        if result.success:
            # Step 3: Save cleaned markdown to disk and remove URL from DLQ
            filename, size_kb = _save(
                result.markdown,
                url,
                output_dir,
                index,
                result.status_code,
                result.metadata,
                frontmatter=frontmatter,
            )
            dlq_store.remove(url, dlq_path)
            print(f"  [{index}] {url}  →  {filename} ({size_kb:.1f} KB, {elapsed:.2f}s)")
            return {"pages": 1, "failed": 0, "total_kb": size_kb, "page_times": [(url, elapsed, size_kb)], "crawled": [(url, os.path.basename(filename))]}

        last_error = result.error_message or "unknown error"
        if attempt < max_retries:
            delay = retry_delay * attempt
            print(f"  ↻ attempt {attempt}/{max_retries} failed: {url} — {last_error} (retry in {delay:.0f}s)")
            await asyncio.sleep(delay)

    # Step 4: All retries exhausted — push URL to DLQ for later retry
    print(f"  ✗ failed after {max_retries} attempts: {url} — {last_error}")
    dlq_store.push(url, last_error, dlq_path)
    return {"pages": 0, "failed": 1, "total_kb": 0.0, "errors": [f"{url}: {last_error}"]}


# ── full-site BFS crawl ───────────────────────────────────────────────────────

async def _crawl_site(
    crawler: AsyncWebCrawler,
    url: str,
    output_dir: str,
    max_depth: int,
    max_pages: int,
    dlq_path: str,
    frontmatter: bool,
) -> dict:
    """BFS-crawl an entire site and stream results to disk. Returns a stats dict."""
    # Step 1: Build BFS config — domain-scoped filter, stream mode, depth/page limits
    domain = urlparse(url).netloc
    config = CrawlerRunConfig(
        **_BASE_CONFIG,
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
    crawled: list[tuple[str, str]] = []
    seen: set[str] = set()

    # Step 2: Stream BFS results — each yielded result is one crawled page
    try:
        stream = await crawler.arun(url=url, config=config)
    except Exception as e:
        message = f"{url}: {e}"
        print(f"  ✗ failed to start crawl: {message}")
        dlq_store.push(url, str(e), dlq_path)
        return {"pages": 0, "failed": 1, "total_kb": 0.0, "page_times": [], "crawled": [], "errors": [message]}

    async for result in stream:
        if not result.success or not result.markdown:
            # Step 2a: Failed page — push to DLQ and continue
            print(f"  ✗ failed: {result.url} — {result.error_message}")
            dlq_store.push(result.url, result.error_message or "unknown error", dlq_path)
            failed += 1
            continue

        # Step 2b: Deduplicate — treat trailing-slash variants as the same page
        # e.g. https://example.com/products/ and https://example.com/products → same page
        normalized = result.url.rstrip("/")
        if normalized in seen:
            print(f"  ~ skipped duplicate: {result.url}")
            continue
        seen.add(normalized)

        # Step 2c: Successful page — save markdown and record (url, filename) for reordering
        pages += 1
        filename, size_kb = _save(
            result.markdown,
            result.url,
            output_dir,
            pages,
            result.status_code,
            result.metadata,
            frontmatter=frontmatter,
        )
        dlq_store.remove(result.url, dlq_path)
        crawled.append((result.url, os.path.basename(filename)))
        page_time = result.metadata.get("timing", {}).get("total", 0.0) if result.metadata else 0.0
        total_kb += size_kb
        page_times.append((result.url, page_time, size_kb))
        print(f"  [{pages}] {result.url}  →  {filename} ({size_kb:.1f} KB)")

    return {"pages": pages, "failed": failed, "total_kb": total_kb, "page_times": page_times, "crawled": crawled, "errors": []}


# ── report ────────────────────────────────────────────────────────────────────

def _report(title: str, stats: dict, elapsed: float, start_res: dict, end_res: dict) -> None:
    pages = stats["pages"]
    page_times = stats.get("page_times", [])
    sorted_times = sorted(page_times, key=lambda x: x[1], reverse=True)
    avg_time = sum(t for _, t, _ in page_times) / pages if pages else 0

    print_report(
        title,
        {
            "Total time":    f"{elapsed:.2f}s",
            "Pages scraped": pages,
            "Pages failed":  stats["failed"],
            "Pages/sec":     f"{pages / elapsed:.2f}" if elapsed else "—",
            "Avg time/page": f"{avg_time:.2f}s",
            "Total content": f"{stats['total_kb']:.1f} KB",
            "Avg page size": f"{stats['total_kb'] / pages:.1f} KB" if pages else "0 KB",
        },
        sections=[
            ("SLOWEST PAGES", [
                f"{t:.2f}s  {s:.1f} KB  {urlparse(u).path}"
                for u, t, s in sorted_times[:5]
            ]),
            ("FASTEST PAGES", [
                f"{t:.2f}s  {s:.1f} KB  {urlparse(u).path}"
                for u, t, s in sorted_times[-5:][::-1]
            ]),
        ] if page_times else None,
        start_resources=start_res,
        end_resources=end_res,
    )


# ── public entry point ────────────────────────────────────────────────────────

async def scrape_url(
    urls: str | list[str],
    mode: Literal["each", "full"] = "each",
    config: UrlIngestorConfig | None = None,
    frontmatter: bool = True,
) -> dict:
    # Step 1: Normalize input — accept a single URL string or a list
    cfg = config or UrlIngestorConfig()
    url_list = [urls] if isinstance(urls, str) else list(urls)
    many = len(url_list) > 1
    os.makedirs(cfg.output_dir, exist_ok=True)

    start = time.time()
    start_res = snapshot()
    totals = {"pages": 0, "failed": 0, "total_kb": 0.0, "page_times": [], "crawled": {}, "files": [], "errors": []}

    # Step 2: Crawl each URL sequentially — one browser session shared across all
    try:
        async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
            for i, url in enumerate(url_list, start=1):
                site_dir = _site_dir(cfg.output_dir, url, many)
                print(f"\n{'─' * 52}")
                print(f"  [{i}/{len(url_list)}] {url}")
                print(f"{'─' * 52}")

                # Step 2a: mode="each" scrapes exactly this URL; mode="full" BFS-crawls the whole site
                if mode == "each":
                    stats = await _crawl_one(
                        crawler,
                        url,
                        site_dir,
                        index=i,
                        dlq_path=cfg.dlq_path,
                        frontmatter=frontmatter,
                    )
                elif mode == "full":
                    stats = await _crawl_site(
                        crawler,
                        url,
                        site_dir,
                        cfg.max_depth,
                        cfg.max_pages,
                        dlq_path=cfg.dlq_path,
                        frontmatter=frontmatter,
                    )
                else:
                    raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")

                # Step 2b: Accumulate stats and crawled (url, filename) pairs per site_dir
                totals["pages"] += stats["pages"]
                totals["failed"] += stats["failed"]
                totals["total_kb"] += stats["total_kb"]
                totals["page_times"].extend(stats.get("page_times", []))
                totals["errors"].extend(stats.get("errors", []))
                totals["crawled"].setdefault(site_dir, []).extend(stats.get("crawled", []))
    except Exception as e:
        message = _browser_setup_error(e)
        print(f"  ✗ {message}")
        totals["failed"] += len(url_list)
        totals["errors"].append(message)

    # Step 3: Print summary report (timing, KB, slowest/fastest pages)
    _report("WEB SCRAPE REPORT", totals, time.time() - start, start_res, snapshot())

    # Step 4: Reorder output files by URL path hierarchy for each site
    for site_dir, crawled in totals["crawled"].items():
        totals["files"].extend(_reorder_by_url_tree(crawled, site_dir))

    # Step 5: Warn if any URLs remain in the DLQ after all retries
    pending = dlq_store.pending(cfg.dlq_path)
    if pending:
        print(f"\n  {len(pending)} URL(s) in DLQ → {cfg.dlq_path}")

    return totals


async def retry_dlq(
    mode: Literal["each", "full"] = "each",
    config: UrlIngestorConfig | None = None,
    max_attempts: int = 3,
) -> dict | None:
    """Re-scrape all URLs in the DLQ that haven't exceeded max_attempts."""
    cfg = config or UrlIngestorConfig()
    urls = dlq_store.pending(cfg.dlq_path, max_attempts=max_attempts)
    if not urls:
        print("DLQ is empty — nothing to retry.")
        return {"pages": 0, "failed": 0, "total_kb": 0.0, "page_times": [], "crawled": {}, "files": [], "errors": []}

    print(f"Retrying {len(urls)} URL(s) from DLQ...")
    return await scrape_url(urls, mode=mode, config=cfg)
