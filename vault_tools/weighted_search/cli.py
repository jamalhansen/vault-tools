"""wsearch: column-weighted BM25 search over vault notes.

    wsearch build [--vault PATH] [--db PATH]
    wsearch query "..." [--db PATH] [--top N] [--weights T,D,B] [--explain]
"""

import argparse
import sys
from pathlib import Path

from vault_tools.shared.vault import resolve_vault
from vault_tools.weighted_search.indexer import build_index
from vault_tools.weighted_search.search import DEFAULT_WEIGHTS, search

DEFAULT_DB = Path.home() / ".cache" / "vault-tools" / "wsearch.duckdb"


def _cmd_build(args: argparse.Namespace) -> None:
    vault = resolve_vault(args.vault)
    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    n = build_index(vault, db_path)
    print(f"Indexed {n} notes from {vault / 'notes'} -> {db_path}")


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="build or rebuild the index")
    build_p.add_argument("--vault", default=None, help="vault path (default: $VAULT_PATH or ~/vaults/Contexta)")
    build_p.add_argument("--db", default=str(DEFAULT_DB), help="index file path")
    build_p.set_defaults(func=_cmd_build)

    query_p = sub.add_parser("query", help="run a weighted BM25 query")
    query_p.add_argument("query")
    query_p.add_argument("--db", default=str(DEFAULT_DB), help="index file path")
    query_p.add_argument("--top", type=int, default=10)
    query_p.add_argument("--weights", default=None, help="title,description,body (default: 10,5,1)")
    query_p.add_argument("--explain", action="store_true", help="show per-field score breakdown")
    query_p.set_defaults(func=_cmd_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
