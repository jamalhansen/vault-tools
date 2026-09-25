"""Shared vault utilities: path resolution and file discovery."""

import os
import sys
from pathlib import Path

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
