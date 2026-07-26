"""Tests for shared vault utilities."""

from pathlib import Path


from vault_tools.shared.vault import find_md_files, parse_frontmatter, read_body
from vault_tools.shared.wiki_links import extract_links, slugify

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseFrontmatter:
    def test_parses_valid_frontmatter(self):
        fm = parse_frontmatter(FIXTURES / "notes" / "note-alpha.md")
        assert fm["type"] == "note"
        assert fm["domain"] == "ai-tools"
        assert fm["description"] == "Alpha is the first note"

    def test_returns_empty_for_no_frontmatter(self, tmp_path):
        f = tmp_path / "plain.md"
        f.write_text("# Just a heading\n\nNo frontmatter.")
        assert parse_frontmatter(f) == {}

    def test_returns_empty_for_missing_file(self, tmp_path):
        assert parse_frontmatter(tmp_path / "nonexistent.md") == {}


class TestReadBody:
    def test_returns_body_after_frontmatter(self):
        body = read_body(FIXTURES / "notes" / "note-alpha.md")
        assert "# Note Alpha" in body
        assert "description:" not in body

    def test_returns_full_text_without_frontmatter(self, tmp_path):
        f = tmp_path / "plain.md"
        f.write_text("Just text.")
        assert read_body(f) == "Just text."


class TestFindMdFiles:
    def test_finds_all_md_files(self):
        files = find_md_files(FIXTURES)
        assert len(files) > 0
        assert all(f.suffix == ".md" for f in files)

    def test_scopes_to_subdir(self):
        files = find_md_files(FIXTURES, subdirs=["notes"])
        paths = [str(f) for f in files]
        assert all("notes" in p for p in paths)


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
