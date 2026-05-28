"""CLI commands for ingestion."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error, parse_pairs, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command("setup-url")
@click.option("--browser", default="chromium", show_default=True, help="Playwright browser to install.")
def setup_url(browser):
    """Install the Playwright browser required for URL ingestion."""
    try:
        RagRails().setup_url(browser=browser)
    except Exception as e:
        exit_with_error(e)


@click.command()
@click.argument("url", nargs=-1, required=True)
@click.option("--mode", default="each", show_default=True, type=click.Choice(["each", "full"]), help="Scrape exact URLs or crawl full sites.")
@click.option("--max-depth", default=3, show_default=True, help="Crawl depth for mode=full.")
@click.option("--max-pages", default=200, show_default=True, help="Max pages per site for mode=full.")
@click.option("--no-frontmatter", is_flag=True, help="Compatibility option; core ingestion does not emit frontmatter.")
def scrape(url, mode, max_depth, max_pages, no_frontmatter):
    """Scrape one or more URLs into markdown output."""
    urls = list(url)
    try:
        result = RagRails().scrape(
            url=urls if len(urls) > 1 else urls[0],
            mode=mode,
            frontmatter=not no_frontmatter,
            max_depth=max_depth,
            max_pages=max_pages,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Pages scraped : {result.pages}")
    click.echo(f"Pages failed  : {result.failed}")
    if result.dlq and result.dlq.path:
        click.echo(f"DLQ           : {result.dlq.path}")
    print_errors(result.errors)


@click.command()
@click.option("--folder", default=None, help="Parse all supported files in this folder.")
@click.option("--files", multiple=True, help="Specific file names to parse (repeatable).")
@click.option("--no-frontmatter", is_flag=True, help="Compatibility option; core ingestion does not emit frontmatter.")
def parse(folder, files, no_frontmatter):
    """Convert local documents into markdown output."""
    if not folder and not files:
        raise click.UsageError("Provide --folder or at least one --files value.")
    if folder and files:
        raise click.UsageError("Use --folder or --files, not both.")

    try:
        result = RagRails().parse(
            files=list(files) if files else None,
            folder=folder,
            frontmatter=not no_frontmatter,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Documents parsed : {result.documents}")
    click.echo(f"Documents failed : {result.failed}")
    print_errors(result.errors)


@click.command()
@click.argument("url")
@click.option("--title", default="API Response", show_default=True, help="Title metadata for the API response.")
@click.option("--description", default="", help="Description metadata for the API response.")
@click.option("--method", default="GET", show_default=True, type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"]), help="HTTP method.")
@click.option("--header", "headers", multiple=True, metavar="KEY:VALUE", help="Request header (repeatable). Example: --header 'Authorization:Bearer token'")
@click.option("--param", "params", multiple=True, metavar="KEY:VALUE", help="Query parameter (repeatable). Example: --param limit:100")
@click.option("--max-pages", default=100, show_default=True, help="Max API pages to fetch.")
@click.option("--no-frontmatter", is_flag=True, help="Compatibility option; core ingestion does not emit frontmatter.")
def fetch(url, title, description, method, headers, params, max_pages, no_frontmatter):
    """Fetch a REST API endpoint into markdown output."""
    try:
        result = RagRails().fetch(
            url=url,
            title=title,
            description=description,
            method=method,
            headers=parse_pairs(headers),
            params=parse_pairs(params),
            max_pages=max_pages,
            frontmatter=not no_frontmatter,
        )
    except click.BadParameter:
        raise
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Documents fetched : {result.documents}")
    click.echo(f"Documents failed  : {result.failed}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(setup_url)
    cli.add_command(scrape)
    cli.add_command(parse)
    cli.add_command(fetch)
