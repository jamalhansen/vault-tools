"""tool-doc-audit: cross-reference BrainSync's local-first tool docs against real disk state.

    tool-doc-audit [--tools-dir PATH] [--projects-dir PATH] [--uv-tools-dir PATH]

Exit code is 1 if any mismatch is found (so it can slot into job-health or a
periodic check), 0 if everything documented matches reality.
"""

import argparse
from pathlib import Path

from local_first_common.tracking import timed_run

from vault_tools.tool_doc_audit.checker import (
    DEFAULT_PROJECTS_DIR,
    DEFAULT_TOOLS_DIR,
    DEFAULT_UV_TOOLS_DIR,
    audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tools-dir", default=str(DEFAULT_TOOLS_DIR))
    parser.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    parser.add_argument("--uv-tools-dir", default=str(DEFAULT_UV_TOOLS_DIR))
    args = parser.parse_args()

    # No LLM model involved (model=None); this just gives tool-doc-audit a
    # heartbeat on the fleet dashboard's activity panel, which vault_tools
    # was invisible to. Findings are computed inside the block (a real run
    # succeeded) but the exit-1-on-findings below happens after it, so
    # "found mismatches" isn't logged as a tracking failure.
    with timed_run("vault-tools", None, source_location=args.tools_dir) as run:
        findings = audit(
            Path(args.tools_dir).expanduser(),
            Path(args.projects_dir).expanduser(),
            Path(args.uv_tools_dir).expanduser(),
        )
        run.item_count = len(findings)

    if not findings:
        print("No mismatches found.")
        return

    for f in findings:
        num = f"#{f.tool_number} " if f.tool_number else ""
        print(f"{num}{f.doc_name}")
        print(f"  status: {f.status!r}, github: {f.github!r}")
        print(f"  {f.issue}")
        print()

    print(f"{len(findings)} mismatch(es) found.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
