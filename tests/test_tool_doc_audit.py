from pathlib import Path

from vault_tools.tool_doc_audit.checker import audit


def _write_doc(tools_dir: Path, name: str, status: str, github: str = "", tool_number: int = 1) -> None:
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / name).write_text(
        f"---\nstatus: {status}\ngithub: '{github}'\ntool_number: {tool_number}\n---\n\n# doc\n"
    )


class TestAudit:
    def test_no_findings_when_everything_matches(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        _write_doc(tools_dir, "01-a.md", status="idea")  # no github, nothing to check
        assert audit(tools_dir, projects_dir, uv_dir) == []

    def test_flags_unbuilt_status_with_real_project_dir(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        (projects_dir / "real-tool").mkdir(parents=True)
        _write_doc(tools_dir, "01-a.md", status="draft", github="https://github.com/jamalhansen/real-tool")

        findings = audit(tools_dir, projects_dir, uv_dir)
        assert len(findings) == 1
        assert "likely built" in findings[0].issue

    def test_flags_unbuilt_status_with_installed_uv_tool(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        (uv_dir / "real-tool").mkdir(parents=True)
        _write_doc(tools_dir, "01-a.md", status="idea", github="https://github.com/jamalhansen/real-tool")

        findings = audit(tools_dir, projects_dir, uv_dir)
        assert len(findings) == 1
        assert "installed uv tool" in findings[0].issue

    def test_flags_built_status_with_no_evidence(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        _write_doc(tools_dir, "01-a.md", status="built", github="https://github.com/jamalhansen/nonexistent-tool")

        findings = audit(tools_dir, projects_dir, uv_dir)
        assert len(findings) == 1
        assert "no project directory or installed uv tool" in findings[0].issue

    def test_decomissioned_status_with_no_evidence_is_not_flagged(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        _write_doc(tools_dir, "01-a.md", status="decomissioned", github="https://github.com/jamalhansen/gone-tool")
        assert audit(tools_dir, projects_dir, uv_dir) == []

    def test_flags_two_docs_sharing_the_same_github_field(self, tmp_path: Path):
        # The real Tool 5 / Tool 15 case: both claimed newsletter-prep-assistant.
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        (projects_dir / "shared-tool").mkdir(parents=True)
        _write_doc(tools_dir, "05-a.md", status="draft", github="https://github.com/jamalhansen/shared-tool", tool_number=5)
        _write_doc(tools_dir, "15-b.md", status="built", github="https://github.com/jamalhansen/shared-tool", tool_number=15)

        findings = audit(tools_dir, projects_dir, uv_dir)
        cross_wire = [f for f in findings if "cross-wire" in f.issue]
        assert len(cross_wire) == 1
        assert cross_wire[0].doc_name == "15-b.md"

    def test_built_status_with_matching_project_dir_is_not_flagged(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        (projects_dir / "real-tool").mkdir(parents=True)
        _write_doc(tools_dir, "01-a.md", status="built", github="https://github.com/jamalhansen/real-tool")
        assert audit(tools_dir, projects_dir, uv_dir) == []

    def test_github_url_with_trailing_slash_and_git_suffix_parses_repo_name(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        projects_dir = tmp_path / "projects"
        uv_dir = tmp_path / "uv-tools"
        (projects_dir / "real-tool").mkdir(parents=True)
        _write_doc(tools_dir, "01-a.md", status="built", github="https://github.com/jamalhansen/real-tool.git")
        assert audit(tools_dir, projects_dir, uv_dir) == []
