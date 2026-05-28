"""Chat tool registry and dispatch."""

from .api_call import API_CALL_TOOL
from .base import ToolSpec
from .web_fetch import WEB_FETCH_TOOL

TOOLS: list[ToolSpec] = [
    API_CALL_TOOL,
    WEB_FETCH_TOOL,
]

_BY_NAME = {tool.name: tool for tool in TOOLS}

# Provider-neutral definitions passed to LLM providers, which adapt to their own API shape.
TOOL_SPECS: list[dict] = [tool.as_dict() for tool in TOOLS]
TOOLS_REQUIRING_CONFIRM: set[str] = {
    tool.name for tool in TOOLS if tool.requires_confirmation
}


def run_tool(name: str, arguments: dict) -> str:
    """Execute a tool call by name and return the result as a string for the LLM."""
    tool = _BY_NAME.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name!r}")
    return tool.run(arguments)


def validate_tool_call(name: str, arguments: dict) -> str | None:
    """Return an error message when a tool call is incomplete or unsafe to execute."""
    tool = _BY_NAME.get(name)
    if tool is None:
        return f"Unknown tool: {name!r}"
    return tool.validate(arguments)
