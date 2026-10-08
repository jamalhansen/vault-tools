"""Tests for shared vault utilities."""

from pathlib import Path

from vault_tools.shared.vault import find_md_files
from vault_tools.shared.wiki_links import extract_links, slugify

FIXTURES = Path(__file__).parent / "fixtures"


class TestFindMdFiles:
    def test_finds_all_md_files(self):
        files = find_md_files(FIXTURES)
        assert len(files) > 0
        assert all(f.suffix == ".md" for f in files)

    def test_scopes_to_subdir(self):
        files = find_md_files(FIXTURES, subdirs=["notes"])
        paths = [str(f) for f in files]
        assert all("notes" in p for p in paths)

    def test_archived_is_left_out_by_default(self, tmp_path):
        (tmp_path / "notes" / "archived").mkdir(parents=True)
        (tmp_path / "notes" / "live.md").write_text("# live\n")
        (tmp_path / "notes" / "archived" / "old.md").write_text("# old\n")
        assert [f.name for f in find_md_files(tmp_path)] == ["live.md"]
        assert [f.name for f in find_md_files(tmp_path, subdirs=["notes"])] == ["live.md"]
        assert [f.name for f in find_md_files(tmp_path, exclude_dirs=frozenset())] == ["old.md", "live.md"]


class TestExtractLinks:
    def test_extracts_simple_links(self):
        links = extract_links("See [[note-alpha]] and [[note-beta]].")
        assert links == ["note-alpha", "note-beta"]

    def test_handles_display_text(self):
        links = extract_links("See [[note-alpha|Alpha Note]].")
        assert links == ["note-alpha"]

    def test_returns_empty_for_no_links(self):
        assert extract_links("No links here.") == []


class TestSlugify:
    def test_lowercases(self):
        assert slugify("Note Alpha") == "note alpha"

    def test_strips_whitespace(self):
        assert slugify("  note  ") == "note"
