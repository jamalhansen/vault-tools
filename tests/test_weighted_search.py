from pathlib import Path

from vault_tools.weighted_search.indexer import build_index
from vault_tools.weighted_search.search import search


def _write_note(vault: Path, name: str, title: str, description: str, body: str) -> None:
    notes_dir = vault / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / name).write_text(
        f"---\ndescription: {description}\n---\n\n# {title}\n\n{body}\n"
    )


def test_title_match_outranks_body_only_match(tmp_path: Path):
    vault = tmp_path / "vault"
    _write_note(
        vault,
        "exact-title.md",
        "column weighted retrieval improves precision",
        "a note about a different topic entirely",
        "nothing relevant here either",
    )
    _write_note(
        vault,
        "body-only.md",
        "an unrelated note about something else",
        "still unrelated",
        "this body happens to mention column weighted retrieval improves precision in passing",
    )

    db_path = tmp_path / "index.duckdb"
    n = build_index(vault, db_path)
    assert n == 2

    results = search(db_path, "column weighted retrieval improves precision", top=10)
    assert len(results) == 2
    assert results[0].id == "notes/exact-title.md"
    assert results[0].weighted_score > results[1].weighted_score


def test_no_matches_returns_empty_list(tmp_path: Path):
    vault = tmp_path / "vault"
    _write_note(vault, "a.md", "some note", "desc", "body text")

    db_path = tmp_path / "index.duckdb"
    build_index(vault, db_path)

    results = search(db_path, "completely unrelated nonexistent gibberish query")
    assert results == []
