"""Shared vault utilities: path resolution, file discovery, frontmatter parsing."""

import os
import sys
from pathlib import Path

import yaml

DEFAULT_VAULT = os.environ.get("VAULT_PATH", str(Path.home() / "vaults" / "Contexta"))


def resolve_vault(path: str | None) -> Path:
    """Resolve vault path from argument, env var, or default. Exits on missing path."""
    raw = path or DEFAULT_VAULT
    vault = Path(raw).expanduser().resolve()
    if not vault.exists():
        print(f"Error: vault path not found: {vault}", file=sys.stderr)
        sys.exit(1)
    return vault


def find_md_files(vault: Path, subdirs: list[str] | None = None) -> list[Path]:
    """Return all .md files in vault, optionally scoped to subdirectories."""
    if subdirs:
        files = []
        for subdir in subdirs:
            files.extend((vault / subdir).rglob("*.md"))
        return sorted(files)
    return sorted(vault.rglob("*.md"))


def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file. Returns {} if none found."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    if not text.startswith("---"):
        return {}

    rest = text[3:]
    end = -1
    for delimiter in ("---", "..."):
        pos = rest.find("\n" + delimiter)
        if pos != -1:
            if end == -1 or pos < end:
                end = pos

    if end == -1:
        return {}

    try:
        data = yaml.safe_load(rest[:end])
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def read_body(filepath: Path) -> str:
    """Return the body text of a markdown file (after frontmatter)."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    if not text.startswith("---"):
        return text

    rest = text[3:]
    end = -1
    for delimiter in ("---", "..."):
        pos = rest.find("\n" + delimiter)
        if pos != -1:
            if end == -1 or pos < end:
                end = pos

    if end == -1:
        return rest

    after = rest[end:]
    newline = after.find("\n")
    return after[newline + 1:] if newline != -1 else ""
