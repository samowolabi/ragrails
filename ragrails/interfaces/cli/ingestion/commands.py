"""CLI commands for ingestion."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error, parse_pairs, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command("setup-url")
@click.option("--browser", default=None, type=click.Choice(["chromium", "firefox", "webkit"]), help="Playwright browser to install.")
@click.option("--verbose", is_flag=True, help="Show the underlying Playwright install command.")
def setup_url(browser, verbose):
    """Install the Playwright browser required for URL ingestion."""
    click.secho("URL ingestion setup", fg="cyan", bold=True)
    click.echo("Prepare browser support for URL scraping.")
    click.echo()
    if browser is None:
        browser = click.prompt(
            "Browser",
            type=click.Choice(["chromium", "firefox", "webkit"], case_sensitive=False),
            default="chromium",
            show_choices=True,
        ).lower()

    click.echo()
    click.echo(f"Installing {browser}...")
    try:
        result = RagRails().setup_url(browser=browser)
    except Exception as e:
        exit_with_error(e)
    click.secho(f"Ready. URL scraping can now use {browser}.", fg="green")
    command = result.get("command") if isinstance(result, dict) else None
    if verbose and command:
        click.echo(f"Command: {' '.join(command)}")
    click.echo()
    click.secho("Next", fg="bright_blue", bold=True)
    click.echo("  ragrails scrape https://example.com/docs --output-dir files/output/web")


@click.command()
@click.argument("url", nargs=-1, required=True)
@click.option("--mode", default="each", show_default=True, type=click.Choice(["each", "full"]), help="Scrape exact URLs or crawl full sites.")
@click.option("--max-depth", default=3, show_default=True, help="Crawl depth for mode=full.")
@click.option("--max-pages", default=200, show_default=True, help="Max pages per site for mode=full.")
@click.option("--frontmatter", is_flag=True, help="Prepend YAML frontmatter to each page.")
@click.option("--output-dir", default=None, help="Save output as JSON files to this directory.")
def scrape(url, mode, max_depth, max_pages, frontmatter, output_dir):
    """Scrape one or more URLs into markdown output."""
    urls = list(url)
    try:
        result = RagRails().scrape(
            url=urls if len(urls) > 1 else urls[0],
            mode=mode,
            frontmatter=frontmatter,
            max_depth=max_depth,
            max_pages=max_pages,
            output_format="json" if output_dir else "markdown",
            output_dest="file" if output_dir else "response",
            output_dir=output_dir,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Pages scraped : {result.pages}")
    click.echo(f"Pages failed  : {result.failed}")
    if output_dir:
        click.echo(f"Output dir    : {output_dir}")
    if result.dlq and result.dlq.path:
        click.echo(f"DLQ           : {result.dlq.path}")
    print_errors(result.errors)


@click.command()
@click.option("--folder", default=None, help="Parse all supported files in this folder.")
@click.option("--files", multiple=True, help="Specific file paths to parse (repeatable).")
@click.option("--frontmatter", is_flag=True, help="Prepend YAML frontmatter to each document.")
@click.option("--output-dir", default=None, help="Save output as JSON files to this directory.")
def parse(folder, files, frontmatter, output_dir):
    """Convert local documents into markdown output."""
    if not folder and not files:
        raise click.UsageError("Provide --folder or at least one --files value.")
    if folder and files:
        raise click.UsageError("Use --folder or --files, not both.")

    try:
        result = RagRails().parse(
            files=list(files) if files else None,
            folder=folder,
            frontmatter=frontmatter,
            output_format="json" if output_dir else "markdown",
            output_dest="file" if output_dir else "response",
            output_dir=output_dir,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Documents parsed : {result.documents}")
    click.echo(f"Documents failed : {result.failed}")
    if output_dir:
        click.echo(f"Output dir       : {output_dir}")
    print_errors(result.errors)


@click.command()
@click.argument("url")
@click.option("--title", default="API Response", show_default=True, help="Title metadata for the API response.")
@click.option("--description", default="", help="Description metadata for the API response.")
@click.option("--method", default="GET", show_default=True, type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"]), help="HTTP method.")
@click.option("--header", "headers", multiple=True, metavar="KEY:VALUE", help="Request header (repeatable). Example: --header 'Authorization:Bearer token'")
@click.option("--param", "params", multiple=True, metavar="KEY:VALUE", help="Query parameter (repeatable). Example: --param limit:100")
@click.option("--max-pages", default=100, show_default=True, help="Max API pages to fetch.")
@click.option("--frontmatter", is_flag=True, help="Prepend YAML frontmatter to each document.")
@click.option("--output-dir", default=None, help="Save output as JSON files to this directory.")
def fetch(url, title, description, method, headers, params, max_pages, frontmatter, output_dir):
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
            frontmatter=frontmatter,
            output_format="json" if output_dir else "markdown",
            output_dest="file" if output_dir else "response",
            output_dir=output_dir,
        )
    except click.BadParameter:
        raise
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Documents fetched : {result.documents}")
    click.echo(f"Documents failed  : {result.failed}")
    if output_dir:
        click.echo(f"Output dir        : {output_dir}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(setup_url)
    cli.add_command(scrape)
    cli.add_command(parse)
    cli.add_command(fetch)
