"""Wiki-link extraction from Obsidian [[note-title]] syntax."""

import re

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def extract_links(text: str) -> list[str]:
    """Extract note titles from [[wiki-link]] and [[wiki-link|display]] syntax.

    Returns the note-title portion only (before | or #), stripped of whitespace.
    Does not deduplicate -- callers can deduplicate if needed.
    """
    return [m.group(1).strip() for m in WIKI_LINK_RE.finditer(text)]


def slugify(title: str) -> str:
    """Convert a wiki-link title to a lowercase slug for file matching."""
    return title.lower().strip()
