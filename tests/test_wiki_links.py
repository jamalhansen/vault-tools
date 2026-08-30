"""Tests for wiki-link extraction."""

from vault_tools.shared.wiki_links import extract_links, slugify


class TestExtractLinks:
    def test_extracts_a_simple_link(self):
        assert extract_links("See [[some-note]] for detail.") == ["some-note"]

    def test_extracts_display_text_link_by_title_only(self):
        assert extract_links("See [[some-note|Some Note]] for detail.") == ["some-note"]

    def test_extracts_multiple_links(self):
        text = "Connects [[note-one]] and [[note-two]]."
        assert extract_links(text) == ["note-one", "note-two"]

    def test_ignores_link_inside_inline_backticks(self):
        # Methodology notes illustrate syntax with `[[note-title]]` -- an example,
        # not a real reference. This is the false-positive bug fixed 2026-08-30.
        text = "Wiki-links look like `[[note-title]]` in Obsidian syntax."
        assert extract_links(text) == []

    def test_ignores_link_inside_fenced_code_block(self):
        text = "```\n[[example-link]]\n```"
        assert extract_links(text) == []

    def test_extracts_real_link_alongside_a_backtick_example(self):
        text = "See [[real-note]] for detail. Syntax looks like `[[note-title]]`."
        assert extract_links(text) == ["real-note"]


class TestSlugify:
    def test_lowercases_and_strips(self):
        assert slugify("  Some Note  ") == "some note"
