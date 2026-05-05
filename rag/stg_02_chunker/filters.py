"""
Chunk and text quality filters.

Responsibilities:
  - Detect and repair mid-link splits across chunk boundaries
  - Strip trailing navigation/footer link blocks from the last chunk
  - Link density utilities
"""

import re


_LINK_PATTERN  = re.compile(r"\[[^\]]+\]\([^)]+\)")
_SKIP_PATTERN  = re.compile(r"\[skip\b", re.IGNORECASE)
_SINGLE_LINK   = re.compile(r"^\s*\[[^\]]+\]\([^)]+\)\s*$")
_HR_PATTERN    = re.compile(r"(\n|^)\s*(\*\s*\*\s*\*|-{3,}|_{3,})\s*$", re.MULTILINE)


def is_link_heavy(text: str, threshold: float = 0.6) -> bool:
    """Return True if markdown links make up more than `threshold` of the text.

    Example:
        is_link_heavy("[Home](/home) [Docs](/docs) [API](/api)")  # → True
        is_link_heavy("Use the `Authorization` header to authenticate.")  # → False
    """
    if not text:
        return False
    link_total = sum(len(m) for m in _LINK_PATTERN.findall(text))
    return link_total / len(text) > threshold


def strip_horizontal_rules(text: str) -> str:
    """Remove trailing markdown horizontal rules (*** --- ___) from chunk text.

    Example:
        strip_horizontal_rules("Use Bearer token auth.\n\n* * *")
        # → "Use Bearer token auth."
    """
    return _HR_PATTERN.sub("", text).strip()


def is_nav_chunk(text: str) -> bool:
    """Return True if the chunk is a navigation-only fragment with no substantive content.

    Catches: "skip to content" links, single bare links, and link-only lines.

    Example:
        is_nav_chunk("[Skip to main content](#main)")  # → True
        is_nav_chunk("Use Bearer token for auth.")     # → False
    """
    stripped = text.strip()
    if _SKIP_PATTERN.search(stripped):
        return True
    if _SINGLE_LINK.match(stripped):
        return True
    lines = [l.strip() for l in stripped.splitlines() if l.strip()]
    if lines and all(_SINGLE_LINK.match(l) for l in lines):
        return True
    return False


def repair_split_links(chunks: list[str]) -> list[str]:
    """Merge any adjacent chunks split in the middle of a markdown link.

    Example:
        repair_split_links(["See [BudPay", "](https://budpay.com) for details"])
        # → ["See [BudPay](https://budpay.com) for details"]
    """
    open_link  = re.compile(r"\[[^\]]*$")
    close_link = re.compile(r"^[^\[]*\]\(")

    repaired: list[str] = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        if i + 1 < len(chunks) and (open_link.search(chunk) or close_link.match(chunks[i + 1])):
            repaired.append(chunk + chunks[i + 1])
            i += 2
        else:
            repaired.append(chunk)
            i += 1
    return repaired


def strip_trailing_nav(chunks: list[dict]) -> list[dict]:
    """Remove trailing link-heavy lines from the last chunk.

    Walks backwards through the final chunk's lines and strips any run of
    link-heavy lines at the end. If the entire last chunk is nav, it is dropped.

    Example:
        chunks[-1]["text"] = "Use Bearer token for auth.\n[Home](/) [Next](/next)"
        strip_trailing_nav(chunks)
        # → chunks[-1]["text"] == "Use Bearer token for auth."
    """
    if not chunks:
        return chunks

    last = chunks[-1]["text"]
    lines = last.splitlines()
    while lines and is_link_heavy(lines[-1]):
        lines.pop()

    stripped = "\n".join(lines).strip()
    if stripped:
        chunks[-1] = {**chunks[-1], "text": stripped}
    else:
        chunks = chunks[:-1]

    return chunks
