"""wsearch: column-weighted BM25 search over vault notes.

    wsearch build [--vault PATH] [--subdirs notes] [--db PATH]
    wsearch query "..." [--db PATH] [--top N] [--weights T,D,B] [--explain]
    wsearch status [--vault PATH] [--subdirs notes] [--db PATH]

One index file per vault by default (~/.cache/vault-tools/wsearch-<vaultname>.duckdb),
so `wsearch query` on a second vault needs --db pointed at that vault's index file --
there's no vault-detection at query time, only at build time.
"""

import argparse
import sys
from pathlib import Path

from local_first_common.tracking import timed_run

from vault_tools.shared.vault import resolve_vault
from vault_tools.weighted_search.indexer import build_index, check_staleness
from vault_tools.weighted_search.search import DEFAULT_WEIGHTS, search

DEFAULT_DB_DIR = Path.home() / ".cache" / "vault-tools"


def _default_db_for(vault: Path) -> Path:
    """One index file per vault name, so indexing a second vault doesn't silently
    overwrite the first vault's index under the same fixed filename."""
    return DEFAULT_DB_DIR / f"wsearch-{vault.name.lower()}.duckdb"


def _cmd_build(args: argparse.Namespace) -> None:
    vault = resolve_vault(args.vault)
    db_path = Path(args.db).expanduser() if args.db else _default_db_for(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    subdirs = [s.strip() for s in args.subdirs.split(",") if s.strip()]
    n = build_index(vault, db_path, subdirs=subdirs)
    print(f"Indexed {n} notes from {vault} ({', '.join(subdirs)}) -> {db_path}")


def _cmd_query(args: argparse.Namespace) -> None:
    db_path = Path(args.db).expanduser()
    weights = DEFAULT_WEIGHTS
    if args.weights:
        parts = [float(x) for x in args.weights.split(",")]
        if len(parts) != 3:
            print("error: --weights needs exactly 3 comma-separated numbers (title,description,body)", file=sys.stderr)
            raise SystemExit(1)
        weights = tuple(parts)

    try:
        results = search(db_path, args.query, top=args.top, weights=weights)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not results:
        print("No matches.")
        return

    for r in results:
        print(f"{r.weighted_score:7.2f}  {r.id}")
        print(f"          {r.title}")
        if args.explain:
            print(
                f"          (title={r.title_score:.3f}*{weights[0]:g}, "
                f"description={r.description_score:.3f}*{weights[1]:g}, "
                f"body={r.body_score:.3f}*{weights[2]:g})"
            )
        print()


def _cmd_status(args: argparse.Namespace) -> None:
    vault = resolve_vault(args.vault)
    db_path = Path(args.db).expanduser() if args.db else _default_db_for(vault)
    subdirs = [s.strip() for s in args.subdirs.split(",") if s.strip()]
    report = check_staleness(vault, db_path, subdirs=subdirs)

    if not report.index_exists:
        print(f"No index at {db_path} -- run 'wsearch build' first.")
        raise SystemExit(1)

    print(f"Index: {db_path}")
    print(f"Built at:        {report.index_built_at.isoformat(sep=' ', timespec='minutes')}")
    print(f"Newest note at:  {report.newest_note_at.isoformat(sep=' ', timespec='minutes') if report.newest_note_at else 'n/a'}")
    print(f"Notes on disk:   {report.note_count}")
    if report.stale:
        print("STALE -- a note has changed since the index was built. Run 'wsearch build'.")
        raise SystemExit(1)
    print("Up to date.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="build or rebuild the index")
    build_p.add_argument("--vault", default=None, help="vault path (default: $VAULT_PATH or ~/vaults/Contexta)")
    build_p.add_argument("--db", default=None, help="index file path (default: one per vault name, see module docstring)")
    build_p.add_argument(
        "--subdirs", default="notes",
        help="comma-separated subdirs to index, relative to --vault (default: notes -- "
             "e.g. Contexta uses notes/, a vault with a different layout like KeySix's "
             "thinking-notes/ needs this set explicitly)",
    )
    build_p.set_defaults(func=_cmd_build)

    query_p = sub.add_parser("query", help="run a weighted BM25 query")
    query_p.add_argument("query")
    query_p.add_argument(
        "--db", default=str(_default_db_for(Path.home() / "vaults" / "Contexta")),
        help="index file path (default: Contexta's index -- pass explicitly for any other vault)",
    )
    query_p.add_argument("--top", type=int, default=10)
    query_p.add_argument("--weights", default=None, help="title,description,body (default: 10,5,1)")
    query_p.add_argument("--explain", action="store_true", help="show per-field score breakdown")
    query_p.set_defaults(func=_cmd_query)

    status_p = sub.add_parser("status", help="check index freshness against the vault's newest note")
    status_p.add_argument("--vault", default=None, help="vault path (default: $VAULT_PATH or ~/vaults/Contexta)")
    status_p.add_argument("--db", default=None, help="index file path (default: one per vault name)")
    status_p.add_argument("--subdirs", default="notes", help="comma-separated subdirs, must match what 'build' used")
    status_p.set_defaults(func=_cmd_status)

    args = parser.parse_args()
    # No LLM model involved (model=None); this just gives wsearch a heartbeat
    # on the fleet dashboard's activity panel, which vault_tools was
    # invisible to. Source location is whichever --db/--vault the subcommand
    # itself resolved, so it's set from inside args.func rather than here.
    with timed_run("vault-tools", None, source_location=getattr(args, "db", None) or getattr(args, "vault", None)):
        args.func(args)


if __name__ == "__main__":
    main()
