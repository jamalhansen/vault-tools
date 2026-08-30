"""Wiki-link extraction from Obsidian [[note-title]] syntax."""

import re

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")

# Methodology notes illustrate wiki-link syntax with examples like `[[note-title]]`,
# deliberately wrapped in backticks so they read as code, not as real links. Until
# 2026-08-30 this module had no code-span awareness at all, so every such example
# counted as a dangling link -- see
# ops/observations/health-check-linter-false-positives-on-backtick-wiki-links.md,
# which was marked "implemented" pointing at a methodology note whose own body said
# "Pending fix". The fix was documented, never coded. This is the actual fix.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code_spans(text: str) -> str:
    """Remove fenced code blocks and inline backtick spans before link scanning."""
    text = _FENCED_CODE_RE.sub("", text)
    return _INLINE_CODE_RE.sub("", text)


def extract_links(text: str) -> list[str]:
    """Extract note titles from [[wiki-link]] and [[wiki-link|display]] syntax.

    Returns the note-title portion only (before | or #), stripped of whitespace.
    Links inside fenced code blocks or inline backtick spans are excluded -- they're
    illustrative syntax examples, not real references. Does not deduplicate --
    callers can deduplicate if needed.
    """
    return [m.group(1).strip() for m in WIKI_LINK_RE.finditer(_strip_code_spans(text))]


def slugify(title: str) -> str:
    """Convert a wiki-link title to a lowercase slug for file matching."""
    return title.lower().strip()
