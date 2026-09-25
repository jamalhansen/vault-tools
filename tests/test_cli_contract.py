"""The command-line contract: what each command prints and exits with, recorded as golden output.

Vault hooks and scripts call these commands by name with specific flags, so a change of
CLI framework must not change them. Each case runs the installed script in a fresh copy
of the fixture vault. Re-record deliberately with RECORD_CLI_CONTRACT=1.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden" / "cli_contract.json"
BIN = Path(sys.executable).parent

CASES = {
    "digest-show": ["vault-digest", "show", "--vault", "{V}"],
    "digest-write-dry": ["vault-digest", "write", "--vault", "{V}", "--dry-run"],
    "digest-write": ["vault-digest", "write", "-v", "{V}", "--verbose"],
    "digest-options-first": ["vault-digest", "--vault", "{V}", "-n", "write"],
    "digest-bad-command": ["vault-digest", "publish", "--vault", "{V}"],
    "tension-rebuild": ["tension-index", "rebuild", "--vault", "{V}"],
    "tension-rebuild-dry-verbose": ["tension-index", "rebuild", "-v", "{V}", "-n", "--verbose"],
    "tension-show-empty": ["tension-index", "show", "--vault", "{V}"],
    "tension-no-command": ["tension-index"],
    "vg-build": ["vg", "--vault", "{V}", "build"],
    "vg-orphans": ["vg", "-v", "{V}", "orphans"],
    "vg-orphans-no-cache": ["vg", "-v", "{V}", "orphans", "--no-cache"],
    "vg-broken": ["vg", "-v", "{V}", "broken", "--no-cache"],
    "vg-backlinks": ["vg", "-v", "{V}", "backlinks", "note-alpha", "--no-cache"],
    "vg-backlinks-none": ["vg", "-v", "{V}", "backlinks", "no-such-note", "--no-cache"],
    "vg-members-missing-map": ["vg", "-v", "{V}", "members"],
    "vg-members": ["vg", "-v", "{V}", "members", "-m", "ai-tools-map", "--no-cache"],
    "wsearch-build": ["wsearch", "build", "--vault", "{V}", "--db", "{T}/idx.duckdb"],
    "wsearch-status-missing": ["wsearch", "status", "--vault", "{V}", "--db", "{T}/none.duckdb"],
    "wsearch-query-missing-db": ["wsearch", "query", "alpha", "--db", "{T}/none.duckdb"],
    "wsearch-bad-weights": ["wsearch", "query", "alpha", "--db", "{T}/none.duckdb", "--weights", "1,2"],
    "tool-doc-audit-empty": ["tool-doc-audit", "--tools-dir", "{T}/tools", "--projects-dir", "{T}", "--uv-tools-dir", "{T}"],
}
# Then, in the same temp dir as wsearch-build:
SEQUENCES = {
    "wsearch-query-sequence": [
        ["wsearch", "build", "--vault", "{V}", "--db", "{T}/idx.duckdb", "--subdirs", "notes"],
        ["wsearch", "query", "alpha", "--db", "{T}/idx.duckdb", "--top", "2", "--explain"],
        ["wsearch", "query", "zzzqqq", "--db", "{T}/idx.duckdb"],
        ["wsearch", "status", "--vault", "{V}", "--db", "{T}/idx.duckdb"],
    ],
    "tension-rebuild-then-show": [
        ["tension-index", "rebuild", "--vault", "{V}"],
        ["tension-index", "show", "--vault", "{V}"],
    ],
}


def _normalize(text: str, tmp: Path) -> str:
    text = text.replace(str(tmp), "<TMP>")
    text = re.sub(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2})?)?", "<DATE>", text)
    return text


def _run(argv: list[str], tmp: Path) -> dict:
    vault = tmp / "vault"
    args = [a.replace("{V}", str(vault)).replace("{T}", str(tmp)) for a in argv]
    env = {**os.environ, "LOCAL_FIRST_TRACKING_DB": str(tmp / "tracking.duckdb"), "HOME": str(tmp)}
    proc = subprocess.run([str(BIN / args[0]), *args[1:]], capture_output=True, text=True, env=env, cwd=tmp, check=False)
    result = {"exit": proc.returncode, "stdout": _normalize(proc.stdout, tmp)}
    if proc.returncode != 2:  # usage errors: only the exit code is part of the contract
        result["stderr"] = _normalize(proc.stderr, tmp)
    return result


def _fresh(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURES, tmp_path / "vault")
    (tmp_path / "tools").mkdir()
    return tmp_path


def _results(tmp_path_factory) -> dict:
    out = {}
    for name, argv in CASES.items():
        out[name] = _run(argv, _fresh(tmp_path_factory.mktemp(name)))
    for name, seq in SEQUENCES.items():
        tmp = _fresh(tmp_path_factory.mktemp(name))
        out[name] = [_run(argv, tmp) for argv in seq]
    return out


def test_cli_contract(tmp_path_factory):
    results = _results(tmp_path_factory)
    if os.environ.get("RECORD_CLI_CONTRACT"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
        pytest.skip("recorded")
    golden = json.loads(GOLDEN.read_text())
    assert set(results) == set(golden)
    for name in golden:
        assert results[name] == golden[name], name
