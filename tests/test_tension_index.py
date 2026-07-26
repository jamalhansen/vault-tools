"""Tests for tension-index parser and index writer."""

from pathlib import Path


from vault_tools.tension_index.index import read_index, write_index
from vault_tools.tension_index.parser import format_row, parse_tension

FIXTURES = Path(__file__).parent / "fixtures"
TENSION_ONE = FIXTURES / "ops" / "tensions" / "tension-one.md"
TENSION_TWO = FIXTURES / "ops" / "tensions" / "tension-two.md"


class TestParseTension:
    def test_parses_tension_with_notes(self):
        t = parse_tension(TENSION_ONE)
        assert t["filename"] == "tension-one.md"
        assert t["status"] == "active"
        assert t["domain"] == "ai-tools"
        assert "note-alpha" in t["notes"]
        assert "note-beta" in t["notes"]

    def test_parses_tension_without_notes(self):
        t = parse_tension(TENSION_TWO)
        assert t["filename"] == "tension-two.md"
        assert t["status"] == "pending"
        assert t["notes"] == []

    def test_description_extracted(self):
        t = parse_tension(TENSION_ONE)
        assert "Speed vs. correctness" in t["description"]


class TestFormatRow:
    def test_formats_with_notes(self):
        t = parse_tension(TENSION_ONE)
        row = format_row(t)
        parts = row.split(" | ")
        assert parts[0] == "tension-one.md"
        assert parts[1] == "active"
        assert parts[2] == "ai-tools"
        assert "note-alpha" in parts[3]

    def test_formats_without_notes(self):
        t = parse_tension(TENSION_TWO)
        row = format_row(t)
        parts = row.split(" | ")
        assert parts[3] == ""  # empty notes field


class TestWriteReadIndex:
    def test_roundtrip(self, tmp_path):
        (tmp_path / "ops").mkdir()
        rows = ["file.md | active | ai-tools |  | a description"]
        write_index(tmp_path, rows)
        result = read_index(tmp_path)
        assert result == rows

    def test_dry_run_does_not_write(self, tmp_path, capsys):
        (tmp_path / "ops").mkdir()
        write_index(tmp_path, ["row1"], dry_run=True)
        assert not (tmp_path / "ops" / "tension-index.md").exists()
        captured = capsys.readouterr()
        assert "row1" in captured.out
