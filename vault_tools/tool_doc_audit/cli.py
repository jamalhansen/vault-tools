"""tool-doc-audit: cross-reference BrainSync's local-first tool docs against real disk state.

    tool-doc-audit [--tools-dir PATH] [--projects-dir PATH] [--uv-tools-dir PATH]

Exit code is 1 if any mismatch is found (so it can slot into job-health or a
periodic check), 0 if everything documented matches reality.
"""

from pathlib import Path
from typing import Annotated

import typer
from local_first_common.tracking import timed_run

from vault_tools.tool_doc_audit.checker import (
    DEFAULT_PROJECTS_DIR,
    DEFAULT_TOOLS_DIR,
    DEFAULT_UV_TOOLS_DIR,
    audit,
)

app = typer.Typer(help=__doc__, add_completion=False)


@app.command()
def main(
    tools_dir: Annotated[str, typer.Option("--tools-dir")] = str(DEFAULT_TOOLS_DIR),
    projects_dir: Annotated[str, typer.Option("--projects-dir")] = str(DEFAULT_PROJECTS_DIR),
    uv_tools_dir: Annotated[str, typer.Option("--uv-tools-dir")] = str(DEFAULT_UV_TOOLS_DIR),
) -> None:
    """Cross-reference the local-first tool docs against real disk state. Exits 1 on any mismatch."""
    # No LLM model involved (model=None); this just gives tool-doc-audit a
    # heartbeat on the fleet dashboard's activity panel, which vault_tools
    # was invisible to. Findings are computed inside the block (a real run
    # succeeded) but the exit-1-on-findings below happens after it, so
    # "found mismatches" isn't logged as a tracking failure.
    with timed_run("vault-tools", None, source_location=tools_dir) as run:
        findings = audit(
            Path(tools_dir).expanduser(),
            Path(projects_dir).expanduser(),
            Path(uv_tools_dir).expanduser(),
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
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
