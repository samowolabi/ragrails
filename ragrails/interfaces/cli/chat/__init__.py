import click


@click.command("chat")
def chat_command() -> None:
    """Start the interactive RAG chat CLI."""
    from .app import main

    main()


def register(cli: click.Group) -> None:
    cli.add_command(chat_command)


__all__ = ["chat_command", "register"]
