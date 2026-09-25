"""vault-digest CLI -- write or show a pre-computed session summary."""

import sys
from enum import Enum
from typing import Annotated

import typer
from local_first_common.tracking import timed_run

from vault_tools.digest.builder import (
    append_session_log,
    build_digest,
    get_orphan_count,
    get_pending_counts,
)
from vault_tools.shared.vault import resolve_vault

DIGEST_PATH = "ops/digest.md"


app = typer.Typer(help="Generate a compact session digest from vault state.", add_completion=False)


class Command(str, Enum):
    write = "write"
    show = "show"


@app.command()
def main(
    command: Annotated[Command, typer.Argument(help="write: save to ops/digest.md; show: print to stdout")],
    vault_path: Annotated[
        str | None, typer.Option("--vault", "-v", help="Path to vault (default: ~/vaults/Contexta)")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n", help="Print without writing")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show extra detail")] = False,
) -> None:
    """Generate a compact session digest from vault state."""
    vault = resolve_vault(vault_path)

    # No LLM model involved (model=None); this just gives vault-digest a
    # heartbeat on the fleet dashboard's activity panel, which vault_tools
    # was invisible to.
    with timed_run("vault-tools", None, source_location=str(vault)) as run:
        run.item_count = 4  # sections

        if verbose:
            print(f"Vault: {vault}", file=sys.stderr)

        digest = build_digest(vault)

        if command == Command.show or dry_run:
            print(digest)
            if dry_run and command == Command.write:
                print("(dry-run: no file written)", file=sys.stderr)
            print("Done. Processed: 4 sections", file=sys.stderr)
            return

        out_path = vault / DIGEST_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(digest, encoding="utf-8")

        counts = get_pending_counts(vault)
        orphan_count = get_orphan_count(vault)
        append_session_log(vault, counts, orphan_count)

        if verbose:
            print(f"Written: {out_path}", file=sys.stderr)
            print(f"Session log: {vault / 'ops/session-log.csv'}", file=sys.stderr)

        print("Done. Processed: 4 sections")


if __name__ == "__main__":
    app()
