"""Tests for wiki-link graph builder and queries."""

from pathlib import Path

import pytest

from vault_tools.wiki_graph.builder import build_graph
from vault_tools.wiki_graph.queries import (
    get_backlinks,
    get_broken,
    get_members,
    get_orphans,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def graph():
    return build_graph(FIXTURES)


class TestBuildGraph:
    def test_indexes_all_md_files(self, graph):
        assert "note-alpha" in graph["file_index"]
        assert "note-beta" in graph["file_index"]
        assert "orphan-note" in graph["file_index"]

    def test_detects_map_notes(self, graph):
        assert "notes-map" in graph["map_notes"]

    def test_captures_outgoing_links(self, graph):
        assert "note-beta" in graph["outgoing"].get("note-alpha", [])
        assert "note-gamma" in graph["outgoing"].get("note-alpha", [])


class TestGetBroken:
    def test_detects_broken_link(self, graph):
        pairs = get_broken(graph["outgoing"], graph["file_index"])
        targets = [t for _, t in pairs]
        assert "note-gamma" in targets  # note-alpha links to note-gamma which doesn't exist

    def test_no_false_positives_for_existing(self, graph):
        pairs = get_broken(graph["outgoing"], graph["file_index"])
        targets = [t for _, t in pairs]
        assert "note-beta" not in targets


class TestGetBacklinks:
    def test_finds_backlinks(self, graph):
        sources = get_backlinks("note-beta", graph["outgoing"])
        assert "note-alpha" in sources

    def test_returns_empty_for_unlinked(self, graph):
        sources = get_backlinks("orphan-note", graph["outgoing"])
        assert sources == []


class TestGetOrphans:
    def test_detects_orphan_note(self, graph):
        orphans = get_orphans(graph["outgoing"], graph["file_index"], graph["map_notes"])
        assert "orphan-note" in orphans

    def test_map_linked_notes_not_orphaned(self, graph):
        orphans = get_orphans(graph["outgoing"], graph["file_index"], graph["map_notes"])
        assert "note-alpha" not in orphans
        assert "note-beta" not in orphans


class TestGetMembers:
    def test_returns_map_members(self, graph):
        members = get_members("notes-map", graph["outgoing"], graph["file_index"])
        assert "note-alpha" in members
        assert "note-beta" in members

    def test_excludes_nonexistent_targets(self, graph):
        members = get_members("notes-map", graph["outgoing"], graph["file_index"])
        assert "note-gamma" not in members
