"""/usage — show local token and cost usage.

Usage:
    /usage

This command reads `files/output/token_usage.jsonl` directly via
`models.llm.usage_logger.summary()`. It is a slash command, so it is handled
before `run_turn()` and never becomes part of conversation history.
"""

from models.llm import usage_logger

from ..session import ChatSession


def handle(args: str, session: ChatSession) -> None:
    """Print token/cost usage summary without calling an LLM."""
    if args.strip():
        print("  Usage: /usage")
        return

    usage_logger.summary()
