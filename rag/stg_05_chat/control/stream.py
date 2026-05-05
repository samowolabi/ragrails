"""/stream — toggle streamed answer output.

Usage:
    /stream          show current stream state
    /stream on       stream plain answers token-by-token
    /stream off      print complete answers after generation
"""

from .. import ui
from ..session import ChatSession


def handle(args: str, session: ChatSession) -> None:
    """Show or update `session.chat_config.stream`."""
    parts = args.split()

    if not parts:
        ui.info("Stream", "on" if session.chat_config.stream else "off")
        return

    if len(parts) == 1 and parts[0].lower() in ("on", "true", "1", "yes"):
        session.chat_config.stream = True
        ui.info("Stream", "on")
        return

    if len(parts) == 1 and parts[0].lower() in ("off", "false", "0", "no"):
        session.chat_config.stream = False
        ui.info("Stream", "off")
        return

    print("  Usage: /stream | /stream on | /stream off")
