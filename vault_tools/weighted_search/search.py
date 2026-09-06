"""Column-weighted BM25 query: title 10x, description 5x, body 1x by default."""

from dataclasses import dataclass
from pathlib import Path

import duckdb

DEFAULT_WEIGHTS = (10.0, 5.0, 1.0)  # title, description, body


@dataclass
class SearchResult:
    id: str
    title: str
    weighted_score: float
    title_score: float
    description_score: float
    body_score: float


def search(
    db_path: Path,
    query: str,
    top: int = 10,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> list[SearchResult]:
    if not db_path.exists():
        raise FileNotFoundError(f"No index at {db_path} -- run 'wsearch build' first")

    title_w, desc_w, body_w = weights
    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("LOAD fts")

    rows = con.execute(
        """
        SELECT
            n.id,
            n.title,
            COALESCE(fts_main_idx_title.match_bm25(n.id, ?), 0.0) AS title_score,
            COALESCE(fts_main_idx_description.match_bm25(n.id, ?), 0.0) AS description_score,
            COALESCE(fts_main_idx_body.match_bm25(n.id, ?), 0.0) AS body_score
        FROM notes n
        """,
        [query, query, query],
    ).fetchall()
    con.close()

    results = [
        SearchResult(
            id=row[0],
            title=row[1],
            title_score=row[2],
            description_score=row[3],
            body_score=row[4],
            weighted_score=row[2] * title_w + row[3] * desc_w + row[4] * body_w,
        )
        for row in rows
    ]
    results = [r for r in results if r.weighted_score > 0]
    results.sort(key=lambda r: r.weighted_score, reverse=True)
    return results[:top]
