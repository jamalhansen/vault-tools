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


# notes/archived/ holds notes /prune moved out of the live set. They keep their
# filenames so old wikilinks still resolve, which also means a plain rglob keeps
# finding them: archived notes were surfacing in wsearch and inflating the wiki
# graph after the 2026-09-26/27 sweep (614 of Contexta's 1,445 notes). Every tool
# gets the live set by default; pass exclude_dirs=frozenset() for everything.
EXCLUDED_DIRS: frozenset[str] = frozenset({"archived"})


def find_md_files(
    vault: Path, subdirs: list[str] | None = None, exclude_dirs: frozenset[str] = EXCLUDED_DIRS
) -> list[Path]:
    """Return the vault's .md files, optionally scoped to subdirectories, skipping any
    file with a path component in exclude_dirs (archived notes, by default)."""
    if subdirs:
        files: list[Path] = []
        for subdir in subdirs:
            files.extend((vault / subdir).rglob("*.md"))
    else:
        files = list(vault.rglob("*.md"))
    return sorted(f for f in files if exclude_dirs.isdisjoint(f.relative_to(vault).parts))
