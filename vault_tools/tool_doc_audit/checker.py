"""Cross-reference BrainSync's local-first tool docs against real disk state.

Built 2026-09-14 after a manual audit (done by hand, took hours across a long
session) found real, concrete drift: 4+ tool docs marked status: draft/idea
despite being fully built and installed as real uv tools; two different docs
(#5 and #15) both claiming the same github repo, because an idea got merged
into another tool and only one doc's github field ever got updated; and a
persona path in _CONTEXT.md that didn't resolve on disk at all. This is that
check, made repeatable instead of re-done by hand next time.

Scope, deliberately: only checks docs whose `github:` field is set. A doc
with an empty github field but a real, differently-named project already
built (the marketing-persona-counsel case, found and fixed by hand this same
session) can't be caught by name-matching alone -- that still needs a human
cross-reference pass. This tool narrows the manual work, it doesn't replace it.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from vault_tools.shared.vault import parse_frontmatter

DEFAULT_TOOLS_DIR = Path.home() / "vaults" / "BrainSync" / "projects" / "local-first" / "tools"
DEFAULT_PROJECTS_DIR = Path.home() / "projects" / "local-first"
DEFAULT_UV_TOOLS_DIR = Path.home() / ".local" / "share" / "uv" / "tools"

# Statuses this vault's tool docs actually use, split by what they imply about
# whether real code should exist. "decomissioned" is deliberately excluded from
# _BUILT_STATUSES' mismatch check -- a decommissioned tool with no trace left
# on disk is expected, not a finding.
_UNBUILT_STATUSES = {"draft", "idea"}
_BUILT_STATUSES = {"built", "live", "complete"}

_GITHUB_RE = re.compile(r"github\.com/[^/]+/([^/#?]+?)(?:\.git)?/?$")


@dataclass
class ToolFinding:
    doc_name: str
    tool_number: int | None
    status: str | None
    github: str | None
    issue: str


def _repo_name_from_github(url: str) -> str | None:
    m = _GITHUB_RE.search(url)
    return m.group(1) if m else None


def audit(
    tools_dir: Path = DEFAULT_TOOLS_DIR,
    projects_dir: Path = DEFAULT_PROJECTS_DIR,
    uv_tools_dir: Path = DEFAULT_UV_TOOLS_DIR,
) -> list[ToolFinding]:
    """Cross-reference every tool doc's status/github claim against real disk state.

    Returns only docs with a real, checkable mismatch -- not a dump of all docs.
    """
    findings: list[ToolFinding] = []
    seen_github: dict[str, str] = {}

    for doc in sorted(tools_dir.glob("*.md")):
        fm = parse_frontmatter(doc)
        status = (fm.get("status") or "").strip().lower() or None
        github = (fm.get("github") or "").strip() or None
        tool_number = fm.get("tool_number")

        repo_name = _repo_name_from_github(github) if github else None
        repo_dir_exists = bool(repo_name and (projects_dir / repo_name).is_dir())
        uv_tool_installed = bool(repo_name and (uv_tools_dir / repo_name).is_dir())
        built_evidence = repo_dir_exists or uv_tool_installed

        if status in _UNBUILT_STATUSES and built_evidence:
            where = "an installed uv tool" if uv_tool_installed else "a project directory"
            findings.append(
                ToolFinding(
                    doc.name, tool_number, status, github,
                    f"status is '{status}' but {where} named '{repo_name}' exists -- likely built and undocumented",
                )
            )
        elif status in _BUILT_STATUSES and github and not built_evidence:
            findings.append(
                ToolFinding(
                    doc.name, tool_number, status, github,
                    f"status is '{status}' but no project directory or installed uv tool named '{repo_name}' was found",
                )
            )

        if github:
            if github in seen_github:
                findings.append(
                    ToolFinding(
                        doc.name, tool_number, status, github,
                        f"github field is identical to {seen_github[github]} -- likely a copy/cross-wire, not two separate tools",
                    )
                )
            else:
                seen_github[github] = doc.name

    return findings
