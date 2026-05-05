"""
/model — list available models and switch the active one mid-conversation.

Usage:
    /model               list available models, mark the active one
    /model gpt-4o        switch to a different model
"""

from .. import ui
from ..model_control import all_models, switch_model
from ..session import ChatSession

_W = 62


def _print_models(session: ChatSession) -> None:
    """Print the model registry, marking the active model with a yellow bullet."""
    print(f"\n  {'─' * _W}")
    print(f"  {'MODEL':<28} DESCRIPTION")
    print(f"  {'─' * _W}")
    current_provider = None
    for m in all_models():
        if m.provider != current_provider:
            current_provider = m.provider
            print(f"  {ui.DIM}{m.provider.upper()}{ui.RESET}")
        active = m.name == session.llm_config.model
        bullet = f"{ui.YELLOW}●{ui.RESET}" if active else "○"
        tag    = f"  {ui.YELLOW}← active{ui.RESET}" if active else ""
        tool_tag = " tools" if m.supports_tools else ""
        print(f"  {bullet}  {m.name:<26} {m.description}{tool_tag}{tag}")
    print(f"  {'─' * _W}\n")


def handle(args: str, session: ChatSession) -> None:
    """List models or switch the active one. Mutates session.llm_config and session.llm.

    Example:
        handle("gpt-4o", session)  # → switches model, prints confirmation
        handle("", session)        # → prints model list
    """
    parts = args.split()

    if not parts:
        _print_models(session)
        return

    if len(parts) == 1:
        result = switch_model(session, parts[0])
        if not result.ok:
            ui.warn(result.message)
            return
        ui.info("Model", result.message)
        return

    print("  Usage: /model | /model <model-name>")
