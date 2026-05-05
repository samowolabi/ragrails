"""
UI helpers — ANSI colors, prompts, and terminal output.
All visual concerns live here so logic modules stay terminal-agnostic.
"""

# ── ANSI ──────────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
BLUE   = "\033[94m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_W      = 60
BORDER  = f"{BLUE}{'═' * _W}{RESET}"
DIVIDER = f"{BLUE}{'─' * _W}{RESET}"


# ── Input ─────────────────────────────────────────────────────────────────────

def prompt() -> str:
    """Read a user input line, return it stripped.

    Example:
        query = prompt()  # → "How do I authenticate?"
    """
    return input(f"{GREEN}Me:{RESET} ").strip()


def confirm_tool_call(name: str, arguments: dict) -> bool:
    """Ask the user to approve a tool call before it executes.

    Example:
        ok = confirm_tool_call("api_call", {"method": "GET", "url": "..."})
        # → True if user typed 'y'
    """
    print(f"\n  {DIVIDER}")
    print(f"  Permission required: {name}")
    for key, val in arguments.items():
        print(f"    {key}: {val}")
    print(f"  {DIVIDER}")
    return input("  Proceed? [y/N] ").strip().lower() == "y"


# ── Output ────────────────────────────────────────────────────────────────────

def welcome() -> None:
    """Print the greeting banner shown at chat startup."""
    print(f"\n{BORDER}")
    print("  RAG Chat — type your question or 'exit' to quit")
    print(f"{BORDER}\n")


def info(label: str, value: str, color: str = CYAN) -> None:
    """Print a labeled value (e.g., session context, model switch).

    Example:
        info("Model", "gpt-4o")
        # → "  Model: gpt-4o"  (label in cyan)
    """
    print(f"  {color}{label}:{RESET} {value}")


def warn(message: str) -> None:
    """Print a non-fatal warning (e.g., 'rewrite failed — using original query')."""
    print(f"  [warn] {message}")


def error(message: str) -> None:
    """Print a recoverable error (e.g., 'retrieval: connection refused')."""
    print(f"  [error] {message}")


def print_answer(answer: str, sources: list[dict]) -> None:
    """Pretty-print a complete assistant answer + its source list."""
    print(f"\n{BORDER}")
    print(f"{BOLD}{answer}{RESET}")
    if sources:
        print(f"\n{DIVIDER}")
        print(f"{DIM}Sources:{RESET}")
        for s in sources:
            print(f"{DIM}  • [{s.get('id', '?')}] {_format_source(s)}{RESET}")
    print(f"{BORDER}\n")


def stream_open() -> None:
    """Open a streaming answer block (border + bold)."""
    print(f"\n{BORDER}")
    print(BOLD, end="", flush=True)


def stream_chunk(chunk: str) -> None:
    """Print one streamed token chunk inline."""
    print(chunk, end="", flush=True)


def stream_close(sources: list[dict]) -> None:
    """Close a streaming answer block (reset bold + sources + border)."""
    print(f"{RESET}\n")
    if sources:
        print(DIVIDER)
        print(f"{DIM}Sources:{RESET}")
        for s in sources:
            print(f"{DIM}  • [{s.get('id', '?')}] {_format_source(s)}{RESET}")
    print(f"{BORDER}\n")


def _format_source(source: dict) -> str:
    """Format one chunk-level source for terminal output."""
    parts = []
    if source.get("title"):
        parts.append(source["title"])
    if source.get("heading"):
        parts.append(source["heading"])

    label = " — ".join(parts) if parts else source.get("chunk_id") or "Untitled chunk"
    if source.get("path"):
        label += f"  {source['path']}"
    if source.get("rerank_score") is not None:
        label += f"  score={source['rerank_score']:.4f}"
    return label
