"""tension-index CLI -- build and display the flat tension index."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from local_first_common.tracking import timed_run

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


app = typer.Typer(help="Build and display the flat tension index.", add_completion=False, no_args_is_help=False)
VaultOption = Annotated[str | None, typer.Option("--vault", "-v")]


@app.callback()
def _root() -> None:
    """Build and display the flat tension index."""


@app.command()
def rebuild(
    vault_path: VaultOption = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Scan ops/tensions/ and rebuild the index."""
    vault = resolve_vault(vault_path)
    # No LLM model involved (model=None); a heartbeat on the fleet dashboard's activity panel.
    with timed_run("vault-tools", None, source_location=str(vault)):
        cmd_rebuild(vault, dry_run=dry_run, verbose=verbose)


@app.command()
def show(vault_path: VaultOption = None) -> None:
    """Print the current index."""
    vault = resolve_vault(vault_path)
    with timed_run("vault-tools", None, source_location=str(vault)):
        cmd_show(vault)


if __name__ == "__main__":
    app()
