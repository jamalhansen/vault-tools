"""vault-tools was one of 7 repos invisible to the fleet dashboard's activity
panel because nothing in it called into local_first_common.tracking. Each of
its five entry points now wraps its work in timed_run under one shared tool
name ("vault-tools"), same pattern as vault-query's three entry points."""

import os
from pathlib import Path

import duckdb
from typer.testing import CliRunner

from vault_tools.digest.cli import app as digest_app
from vault_tools.tension_index.cli import app as tension_index_app
from vault_tools.tool_doc_audit.cli import app as tool_doc_audit_app
from vault_tools.wiki_graph.cli import app as vg_app

runner = CliRunner()

FIXTURES = Path(__file__).parent / "fixtures"


def _tracking_db():
    return duckdb.connect(os.environ["LOCAL_FIRST_TRACKING_DB"])


def _last_run():
    return _tracking_db().execute(
        "SELECT tool_name, success FROM processing_log "
        "WHERE tool_name = 'vault-tools' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()


def test_vault_digest_logs_a_run():
    assert runner.invoke(digest_app, ["show", "--vault", str(FIXTURES)]).exit_code == 0
    assert _last_run() == ("vault-tools", True)


def test_tension_index_logs_a_run(tmp_path):
    (tmp_path / "ops" / "tensions").mkdir(parents=True)
    assert runner.invoke(tension_index_app, ["show", "--vault", str(tmp_path)]).exit_code == 0
    assert _last_run() == ("vault-tools", True)


def test_vg_logs_a_run(tmp_path):
    (tmp_path / "notes").mkdir()
    assert runner.invoke(vg_app, ["--vault", str(tmp_path), "build"]).exit_code == 0
    assert _last_run() == ("vault-tools", True)


def test_tool_doc_audit_findings_are_not_logged_as_a_failure(tmp_path):
    """The CLI exits 1 when it finds mismatches -- that's the tool working
    correctly, not a crash, and must not show up as a tracking failure."""
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(
        tool_doc_audit_app,
        ["--tools-dir", str(empty), "--projects-dir", str(empty), "--uv-tools-dir", str(empty)],
    )
    assert result.exit_code == 0  # no findings possible against empty dirs
    assert _last_run() == ("vault-tools", True)
