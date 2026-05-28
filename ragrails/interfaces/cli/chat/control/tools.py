"""/tools — list locally registered chat tools.

Usage:
    /tools

This command only reads the local tool registry. It does not call the LLM and
does not enter conversation history.
"""

from ..session import ChatSession
from ..tools import TOOLS


def handle(args: str, session: ChatSession) -> None:
    """Print registered tool names, required fields, and confirmation policy."""
    if args.strip():
        print("  Usage: /tools")
        return

    print("\n  ────────────────────────────────────────────────────────────")
    print("  TOOLS")
    print("  ────────────────────────────────────────────────────────────")
    for tool in TOOLS:
        required = tool.input_schema.get("required", [])
        required_text = ", ".join(required) if required else "none"
        confirmation = "yes" if tool.requires_confirmation else "no"
        strict = "yes" if tool.strict else "no"

        print(f"  {tool.name}")
        print(f"    confirmation: {confirmation}")
        print(f"    strict:       {strict}")
        print(f"    required:     {required_text}")
        print(f"    description:  {tool.description}")
    print("  ────────────────────────────────────────────────────────────\n")
