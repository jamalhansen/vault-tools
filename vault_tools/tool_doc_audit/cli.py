"""tool-doc-audit: cross-reference BrainSync's local-first tool docs against real disk state.

    tool-doc-audit [--tools-dir PATH] [--projects-dir PATH] [--uv-tools-dir PATH]

Exit code is 1 if any mismatch is found (so it can slot into job-health or a
periodic check), 0 if everything documented matches reality.
"""

import argparse
from pathlib import Path

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

    findings = audit(
        Path(args.tools_dir).expanduser(),
        Path(args.projects_dir).expanduser(),
        Path(args.uv_tools_dir).expanduser(),
    )

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
