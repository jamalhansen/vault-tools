"""tension-index CLI -- build and display the flat tension index."""

import argparse
import sys
from pathlib import Path

from vault_tools.shared.vault import resolve_vault
from vault_tools.tension_index.index import INDEX_PATH, read_index, write_index
from vault_tools.tension_index.parser import format_row, parse_tension


def cmd_rebuild(vault: Path, dry_run: bool, verbose: bool) -> None:
    tensions_dir = vault / "ops" / "tensions"
    if not tensions_dir.exists():
        print(f"Error: tensions directory not found: {tensions_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(tensions_dir.glob("*.md"))
    rows = []
    for f in files:
        tension = parse_tension(f)
        if f.name.endswith(".archived.md"):
            tension["status"] = "archived"
        rows.append(format_row(tension))
        if verbose:
            print(f"  {f.name} [{tension['status']}]", file=sys.stderr)

    write_index(vault, rows, dry_run=dry_run)

    if not dry_run:
        print(f"Done. Processed: {len(files)} tensions")
    else:
        print(f"(dry-run: {len(files)} tensions, no file written)", file=sys.stderr)


def cmd_show(vault: Path) -> None:
    rows = read_index(vault)
    if not rows:
        print("(tension index is empty -- run: tension-index rebuild)")
        return
    path = vault / INDEX_PATH
    print(f"# {path}")
    for row in rows:
        print(row)
    print(f"\n{len(rows)} tensions indexed")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tension-index",
        description="Build and display the flat tension index.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    rebuild_p = sub.add_parser("rebuild", help="Scan ops/tensions/ and rebuild the index")
    rebuild_p.add_argument("--vault", "-v", default=None)
    rebuild_p.add_argument("--dry-run", "-n", action="store_true")
    rebuild_p.add_argument("--verbose", action="store_true")

    show_p = sub.add_parser("show", help="Print the current index")
    show_p.add_argument("--vault", "-v", default=None)

    args = parser.parse_args()
    vault = resolve_vault(args.vault)

    if args.command == "rebuild":
        cmd_rebuild(vault, dry_run=args.dry_run, verbose=args.verbose)
    elif args.command == "show":
        cmd_show(vault)


if __name__ == "__main__":
    main()
