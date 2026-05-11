"""
Run:
    uv run python -m ragrails.pipeline.stg_05_chat
"""

from . import ui
from .config import ChatConfig
from .control import handle as handle_command, is_command
from .pipeline import run_turn
from .session import build_session


def main() -> None:
    session = build_session(ChatConfig(
        persona="You are an OpenCode assistant, an AI coding agent built for the terminal. You help developers understand OpenCode's features, configuration, providers, and usage — answering questions grounded in the official OpenCode documentation.",
    ))
    ui.welcome()

    while True:
        try:
            query = ui.prompt()
        except (KeyboardInterrupt, EOFError):
            session.shutdown()
            print("\nBye.")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "q"):
            session.shutdown()
            print("Bye.")
            break
        if is_command(query):
            handle_command(query, session)
            continue

        response = run_turn(query, session)
        if not response.rendered:
            ui.print_answer(response.answer, response.sources)


if __name__ == "__main__":
    main()
