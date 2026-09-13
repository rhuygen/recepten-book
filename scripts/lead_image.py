"""Shared parsing for a recipe's lead image, used by both the PDF build
(scripts/build_pdf.py) and the website build (scripts/mkdocs_lead_image.py).

A recipe's lead image is its first block, when that block is a standalone
Markdown image. It may set its own column width with a `|<width>` suffix
on the alt text, for example:

    ![Erwtensoep|30%](../Images/erwtensoep.jpg)

Both outputs place this image beside the first heading immediately
followed by a list (the ingredients, whatever that section happens to be
titled), keeping everything before it (the title, any intro text)
full-width. See CLAUDE.md for why.
"""

from __future__ import annotations

import re

IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]*)\)$")
LIST_ITEM_RE = re.compile(r"^(-|\*|\+|\d+\.)\s")
WIDTH_VALUE_RE = re.compile(r"^\d+(\.\d+)?%$")


def split_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n+", text.strip()) if b.strip()]


def is_heading(block: str) -> bool:
    return block.startswith("#")


def is_list(block: str) -> bool:
    return bool(LIST_ITEM_RE.match(block.splitlines()[0].strip()))


def parse_lead_image(blocks: list[str], source_name: str) -> tuple[str, str, str | None] | None:
    """If blocks[0] is a standalone image, return (alt_text, ref, width).

    alt_text has the `|<width>` suffix stripped; width is None when the
    recipe did not set one. Returns None when blocks[0] is not an image.
    """
    if not blocks:
        return None
    match = IMAGE_RE.match(blocks[0])
    if not match:
        return None

    alt_text, ref = match.groups()
    width = None
    if "|" in alt_text:
        alt_text, _, width = alt_text.rpartition("|")
        if not WIDTH_VALUE_RE.match(width):
            raise SystemExit(f"{source_name}: invalid |<width> suffix {width!r}, expected a percentage like '30%'")
    return alt_text, ref, width


def find_heading_list_pair(blocks: list[str]) -> int | None:
    """Index of the first heading immediately followed by a list, or None."""
    return next(
        (i for i in range(len(blocks) - 1) if is_heading(blocks[i]) and is_list(blocks[i + 1])),
        None,
    )
