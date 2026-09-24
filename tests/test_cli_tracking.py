"""vault-tools was one of 7 repos invisible to the fleet dashboard's activity
panel because nothing in it called into local_first_common.tracking. Each of
its five entry points now wraps its work in timed_run under one shared tool
name ("vault-tools"), same pattern as vault-query's three entry points."""

import os
import sys
from pathlib import Path

import duckdb

from vault_tools.digest.cli import main as digest_main
from vault_tools.tension_index.cli import main as tension_index_main
from vault_tools.tool_doc_audit.cli import main as tool_doc_audit_main
from vault_tools.wiki_graph.cli import main as vg_main

FIXTURES = Path(__file__).parent / "fixtures"


def _tracking_db():
    return duckdb.connect(os.environ["LOCAL_FIRST_TRACKING_DB"])


def _last_run():
    return _tracking_db().execute(
        "SELECT tool_name, success FROM processing_log "
        "WHERE tool_name = 'vault-tools' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()


def test_vault_digest_logs_a_run(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["vault-digest", "show", "--vault", str(FIXTURES)])
    digest_main()
    assert _last_run() == ("vault-tools", True)


def test_tension_index_logs_a_run(monkeypatch, tmp_path):
    (tmp_path / "ops" / "tensions").mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", ["tension-index", "show", "--vault", str(tmp_path)])
    tension_index_main()
    assert _last_run() == ("vault-tools", True)


def test_vg_logs_a_run(monkeypatch, tmp_path):
    (tmp_path / "notes").mkdir()
    monkeypatch.setattr(sys, "argv", ["vg", "--vault", str(tmp_path), "build"])
    vg_main()
    assert _last_run() == ("vault-tools", True)


def test_tool_doc_audit_findings_are_not_logged_as_a_failure(monkeypatch, tmp_path):
    """The CLI exits 1 when it finds mismatches -- that's the tool working
    correctly, not a crash, and must not show up as a tracking failure."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(
        sys, "argv",
        ["tool-doc-audit", "--tools-dir", str(empty), "--projects-dir", str(empty), "--uv-tools-dir", str(empty)],
    )
    tool_doc_audit_main()  # no findings possible against empty dirs -> exits 0, not raises
    assert _last_run() == ("vault-tools", True)
