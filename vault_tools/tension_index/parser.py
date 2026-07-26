"""Parse tension files into index rows."""

import re
from pathlib import Path

from vault_tools.shared.vault import parse_frontmatter

_BRACKET_RE = re.compile(r"^\[\[(.+)\]\]$")


def _clean_note_ref(raw: str) -> str:
    """Strip [[ ]] wrappers from a note reference if present."""
    raw = raw.strip()
    m = _BRACKET_RE.match(raw)
    return m.group(1).strip() if m else raw


def parse_tension(path: Path) -> dict:
    """Extract index fields from a tension file.

    Returns a dict with: filename, status, domain, description, notes (list).
    """
    fm = parse_frontmatter(path)
    raw_notes = fm.get("notes") or []
    if isinstance(raw_notes, str):
        raw_notes = [raw_notes]

    notes = [_clean_note_ref(str(n)) for n in raw_notes if n]

    return {
        "filename": path.name,
        "status": str(fm.get("status", "unknown")),
        "domain": str(fm.get("domain", "")),
        "description": str(fm.get("description", "")).strip(),
        "notes": notes,
    }


def format_row(tension: dict) -> str:
    """Format a tension dict as a pipe-delimited index row."""
    notes_str = ", ".join(tension["notes"]) if tension["notes"] else ""
    return " | ".join([
        tension["filename"],
        tension["status"],
        tension["domain"],
        notes_str,
        tension["description"],
    ])
