"""Builds a column-weighted BM25 index over vault notes.

Title, description, and body are indexed as three separate DuckDB FTS indexes
(DuckDB's FTS extension supports one index per table, so each field gets its
own table) rather than one combined index, so each field's BM25 score can be
weighted independently before combining. See:
notes/column-weighted-bm25-improves-precision-for-structured-notes-by-scoring-title-matches-far-above-body-matches.md
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb

from local_first_common.obsidian import parse_frontmatter, read_body

from vault_tools.shared.vault import find_md_files

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _extract_title(body: str) -> str:
    m = _TITLE_RE.search(body)
    return m.group(1).strip() if m else ""


def _strip_title_line(body: str) -> str:
    return _TITLE_RE.sub("", body, count=1)


def build_index(vault: Path, db_path: Path, subdirs: list[str] | None = None) -> int:
    """(Re)build the index. Returns the number of notes indexed.

    `subdirs` defaults to ["notes"] -- Contexta's layout. A vault with a different
    layout (e.g. KeySix's thinking-notes/) must pass its own subdirs explicitly;
    there's no vault-detection magic here.
    """
    files = find_md_files(vault, subdirs=subdirs or ["notes"])

    rows = []
    for f in files:
        fm = parse_frontmatter(f)
        raw_body = read_body(f)
        title = _extract_title(raw_body)
        body = _strip_title_line(raw_body)
        description = fm.get("description", "") or ""
        rel_id = str(f.relative_to(vault))
        rows.append((rel_id, title, description, body))

    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    con.execute("INSTALL fts")
    con.execute("LOAD fts")
    con.execute("CREATE TABLE notes (id VARCHAR, title VARCHAR, description VARCHAR, body VARCHAR)")
    if rows:
        con.executemany("INSERT INTO notes VALUES (?, ?, ?, ?)", rows)

    con.execute("CREATE TABLE idx_title AS SELECT id, title FROM notes")
    con.execute("CREATE TABLE idx_description AS SELECT id, description FROM notes")
    con.execute("CREATE TABLE idx_body AS SELECT id, body FROM notes")

    con.execute("PRAGMA create_fts_index('idx_title', 'id', 'title')")
    con.execute("PRAGMA create_fts_index('idx_description', 'id', 'description')")
    con.execute("PRAGMA create_fts_index('idx_body', 'id', 'body')")

    con.close()
    return len(rows)


@dataclass
class StalenessReport:
    index_exists: bool
    index_built_at: datetime | None
    newest_note_at: datetime | None
    stale: bool  # True if the index predates the newest note, or doesn't exist at all
    note_count: int


def check_staleness(vault: Path, db_path: Path, subdirs: list[str] | None = None) -> StalenessReport:
    """Compare the index file's mtime against the newest note's mtime.

    Written 2026-09-14 after a real incident: Contexta's index sat a week stale
    (1,173 notes at last build vs. 1,323 real) before anyone noticed, because
    nothing ever checked -- `build` has to be run manually and nothing flagged
    that it hadn't been.
    """
    files = find_md_files(vault, subdirs=subdirs or ["notes"])
    newest = max((f.stat().st_mtime for f in files), default=None)
    newest_dt = datetime.fromtimestamp(newest) if newest is not None else None

    if not db_path.exists():
        return StalenessReport(False, None, newest_dt, True, len(files))

    built_dt = datetime.fromtimestamp(db_path.stat().st_mtime)
    stale = newest_dt is not None and newest_dt > built_dt
    return StalenessReport(True, built_dt, newest_dt, stale, len(files))
