"""wsearch: column-weighted BM25 search over vault notes.

    wsearch build [--vault PATH] [--subdirs notes] [--db PATH]
    wsearch query "..." [--db PATH] [--top N] [--weights T,D,B] [--explain]
    wsearch status [--vault PATH] [--subdirs notes] [--db PATH]

One index file per vault by default (~/.cache/vault-tools/wsearch-<vaultname>.duckdb),
so `wsearch query` on a second vault needs --db pointed at that vault's index file --
there's no vault-detection at query time, only at build time.
"""

import sys
from pathlib import Path
from typing import Annotated

import typer
from local_first_common.tracking import timed_run

from vault_tools.shared.vault import resolve_vault
from vault_tools.weighted_search.indexer import build_index, check_staleness
from vault_tools.weighted_search.search import DEFAULT_WEIGHTS, search

DEFAULT_DB_DIR = Path.home() / ".cache" / "vault-tools"


def _default_db_for(vault: Path) -> Path:
    """One index file per vault name, so indexing a second vault doesn't silently
    overwrite the first vault's index under the same fixed filename."""
    return DEFAULT_DB_DIR / f"wsearch-{vault.name.lower()}.duckdb"


app = typer.Typer(help=__doc__, add_completion=False)
VaultOption = Annotated[
    str | None, typer.Option("--vault", help="vault path (default: $VAULT_PATH or ~/vaults/Contexta)")
]


@app.callback()
def _root() -> None:
    """Column-weighted BM25 search over vault notes."""


# No LLM model involved (model=None); each command gives wsearch a heartbeat on the
# fleet dashboard's activity panel, which vault_tools was invisible to.


@app.command()
def build(
    vault: VaultOption = None,
    db: Annotated[str | None, typer.Option("--db", help="index file path (default: one per vault name)")] = None,
    subdirs: Annotated[
        str,
        typer.Option(
            "--subdirs",
            help="comma-separated subdirs to index, relative to --vault (default: notes -- "
                 "e.g. Contexta uses notes/, a vault with a different layout like KeySix's "
                 "thinking-notes/ needs this set explicitly)",
        ),
    ] = "notes",
) -> None:
    """Build or rebuild the index."""
    with timed_run("vault-tools", None, source_location=db or vault):
        vault_path = resolve_vault(vault)
        db_path = Path(db).expanduser() if db else _default_db_for(vault_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        dirs = [s.strip() for s in subdirs.split(",") if s.strip()]
        n = build_index(vault_path, db_path, subdirs=dirs)
        print(f"Indexed {n} notes from {vault_path} ({', '.join(dirs)}) -> {db_path}")


@app.command()
def query(
    query: Annotated[str, typer.Argument()],
    db: Annotated[
        str, typer.Option("--db", help="index file path (default: Contexta's index -- pass explicitly for any other vault)")
    ] = str(_default_db_for(Path.home() / "vaults" / "Contexta")),
    top: Annotated[int, typer.Option("--top")] = 10,
    weights_arg: Annotated[str | None, typer.Option("--weights", help="title,description,body (default: 10,5,1)")] = None,
    explain: Annotated[bool, typer.Option("--explain", help="show per-field score breakdown")] = False,
) -> None:
    """Run a weighted BM25 query."""
    with timed_run("vault-tools", None, source_location=db):
        db_path = Path(db).expanduser()
        weights = DEFAULT_WEIGHTS
        if weights_arg:
            parts = [float(x) for x in weights_arg.split(",")]
            if len(parts) != 3:
                print("error: --weights needs exactly 3 comma-separated numbers (title,description,body)", file=sys.stderr)
                raise typer.Exit(1)
            weights = tuple(parts)

        try:
            results = search(db_path, query, top=top, weights=weights)
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            raise typer.Exit(1) from e

        if not results:
            print("No matches.")
            return

        for r in results:
            print(f"{r.weighted_score:7.2f}  {r.id}")
            print(f"          {r.title}")
            if explain:
                print(
                    f"          (title={r.title_score:.3f}*{weights[0]:g}, "
                    f"description={r.description_score:.3f}*{weights[1]:g}, "
                    f"body={r.body_score:.3f}*{weights[2]:g})"
                )
            print()


@app.command()
def status(
    vault: VaultOption = None,
    db: Annotated[str | None, typer.Option("--db", help="index file path (default: one per vault name)")] = None,
    subdirs: Annotated[str, typer.Option("--subdirs", help="comma-separated subdirs, must match what 'build' used")] = "notes",
) -> None:
    """Check index freshness against the vault's newest note."""
    with timed_run("vault-tools", None, source_location=db or vault):
        vault_path = resolve_vault(vault)
        db_path = Path(db).expanduser() if db else _default_db_for(vault_path)
        dirs = [s.strip() for s in subdirs.split(",") if s.strip()]
        report = check_staleness(vault_path, db_path, subdirs=dirs)

        if not report.index_exists:
            print(f"No index at {db_path} -- run 'wsearch build' first.")
            raise typer.Exit(1)

        print(f"Index: {db_path}")
        print(f"Built at:        {report.index_built_at.isoformat(sep=' ', timespec='minutes')}")
        print(f"Newest note at:  {report.newest_note_at.isoformat(sep=' ', timespec='minutes') if report.newest_note_at else 'n/a'}")
        print(f"Notes on disk:   {report.note_count}")
        if report.stale:
            print("STALE -- a note has changed since the index was built. Run 'wsearch build'.")
            raise typer.Exit(1)
        print("Up to date.")


if __name__ == "__main__":
    app()
