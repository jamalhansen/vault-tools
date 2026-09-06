"""Builds a column-weighted BM25 index over vault notes.

Title, description, and body are indexed as three separate DuckDB FTS indexes
(DuckDB's FTS extension supports one index per table, so each field gets its
own table) rather than one combined index, so each field's BM25 score can be
weighted independently before combining. See:
notes/column-weighted-bm25-improves-precision-for-structured-notes-by-scoring-title-matches-far-above-body-matches.md
"""

import re
from pathlib import Path

import duckdb

from vault_tools.shared.vault import find_md_files, parse_frontmatter, read_body

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _extract_title(body: str) -> str:
    m = _TITLE_RE.search(body)
    return m.group(1).strip() if m else ""


def _strip_title_line(body: str) -> str:
    return _TITLE_RE.sub("", body, count=1)


def build_index(vault: Path, db_path: Path) -> int:
    """(Re)build the index. Returns the number of notes indexed."""
    files = find_md_files(vault, subdirs=["notes"])

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
    con.executemany("INSERT INTO notes VALUES (?, ?, ?, ?)", rows)

    con.execute("CREATE TABLE idx_title AS SELECT id, title FROM notes")
    con.execute("CREATE TABLE idx_description AS SELECT id, description FROM notes")
    con.execute("CREATE TABLE idx_body AS SELECT id, body FROM notes")

    con.execute("PRAGMA create_fts_index('idx_title', 'id', 'title')")
    con.execute("PRAGMA create_fts_index('idx_description', 'id', 'description')")
    con.execute("PRAGMA create_fts_index('idx_body', 'id', 'body')")

    con.close()
    return len(rows)
