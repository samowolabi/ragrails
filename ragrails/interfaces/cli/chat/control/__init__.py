"""
Control module — handles all slash commands in the chat interface.

Adding a new command:
    1. Create ragrails/core/stg_06_chat/control/<name>.py with a handle(args, session) function.
    2. Register its prefix in COMMANDS below.
"""

from ..session import ChatSession
from . import debug, model, stream, tools, usage

# Command registry: prefix → handler module exposing handle(args, session)
COMMANDS: dict[str, object] = {
    "/debug": debug,
    "/model": model,
    "/stream": stream,
    "/tools": tools,
    "/usage": usage,
}


def is_command(query: str) -> bool:
    """Return True if the query starts with a registered slash command.

    Example:
        is_command("/model gpt-4o")  # → True
        is_command("how do I pay")   # → False
    """
    command, _, _ = query.partition(" ")
    return command in COMMANDS


def handle(query: str, session: ChatSession) -> None:
    """Dispatch a slash command to its handler. Mutates session.

    Example:
        handle("/model gpt-4o", session)   # → switches model
    """
    command, _, args = query.partition(" ")
    mod = COMMANDS.get(command)
    if mod is not None:
        mod.handle(args.strip(), session)
