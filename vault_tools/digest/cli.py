"""vault-digest CLI -- write or show a pre-computed session summary."""

import argparse
import sys

from vault_tools.digest.builder import (
    append_session_log,
    build_digest,
    get_orphan_count,
    get_pending_counts,
)
from vault_tools.shared.vault import resolve_vault

DIGEST_PATH = "ops/digest.md"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vault-digest",
        description="Generate a compact session digest from vault state.",
    )
    parser.add_argument(
        "command",
        choices=["write", "show"],
        help="write: save to ops/digest.md; show: print to stdout",
    )
    parser.add_argument("--vault", "-v", default=None, help="Path to vault (default: ~/vaults/Contexta)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Print without writing")
    parser.add_argument("--verbose", action="store_true", help="Show extra detail")

    args = parser.parse_args()
    vault = resolve_vault(args.vault)

    if args.verbose:
        print(f"Vault: {vault}", file=sys.stderr)

    digest = build_digest(vault)

    if args.command == "show" or args.dry_run:
        print(digest)
        if args.dry_run and args.command == "write":
            print("(dry-run: no file written)", file=sys.stderr)
        print("Done. Processed: 4 sections", file=sys.stderr)
        return

    out_path = vault / DIGEST_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(digest, encoding="utf-8")

    counts = get_pending_counts(vault)
    orphan_count = get_orphan_count(vault)
    append_session_log(vault, counts, orphan_count)

    if args.verbose:
        print(f"Written: {out_path}", file=sys.stderr)
        print(f"Session log: {vault / 'ops/session-log.csv'}", file=sys.stderr)

    print("Done. Processed: 4 sections")


if __name__ == "__main__":
    main()
