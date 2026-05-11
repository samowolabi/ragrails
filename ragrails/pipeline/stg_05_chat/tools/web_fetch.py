"""web_fetch tool implementation."""

from markitdown import MarkItDown

from .base import ToolSpec

_MAX_FETCH_CHARS = 8_000

def run_web_fetch(url: str) -> str:
    """Fetch a URL and return its content as clean markdown text."""
    try:
        md = MarkItDown()
        text = md.convert(url).text_content.strip()
        if len(text) > _MAX_FETCH_CHARS:
            text = text[:_MAX_FETCH_CHARS] + "\n\n[content trimmed]"
        return text or "Page fetched but no readable content found."
    except Exception as e:
        return f"Failed to fetch {url}: {e}"


def validate_web_fetch(arguments: dict) -> str | None:
    if not arguments.get("url"):
        return "web_fetch requires url."
    return None


WEB_FETCH_TOOL = ToolSpec(
    name="web_fetch",
    description=(
        "Fetch a webpage and return its content as readable text. "
        "Use this when the documentation does not have enough information — "
        "for example, to search the web (use a DuckDuckGo or Google search URL), "
        "fetch a specific page the user points you to, or look up external references."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch.",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
    handler=lambda arguments: run_web_fetch(arguments["url"]),
    validator=validate_web_fetch,
    requires_confirmation=False,
    strict=True,
)
