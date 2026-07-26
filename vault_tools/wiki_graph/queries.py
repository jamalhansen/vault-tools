"""Graph query functions: orphans, broken links, backlinks, map members."""

from vault_tools.shared.wiki_links import slugify


def build_incoming(outgoing: dict[str, list[str]]) -> dict[str, list[str]]:
    """Invert outgoing index to build incoming (backlink) index."""
    incoming: dict[str, list[str]] = {slug: [] for slug in outgoing}
    for source, targets in outgoing.items():
        for target in targets:
            if target not in incoming:
                incoming[target] = []
            incoming[target].append(source)
    return incoming


def get_broken(outgoing: dict[str, list[str]], file_index: dict[str, str]) -> list[tuple[str, str]]:
    """Return (source, broken_target) pairs for links with no matching file.

    Cross-vault links (no file match) are included -- callers may want to filter.
    """
    broken = []
    for source, targets in outgoing.items():
        for target in targets:
            if target not in file_index:
                broken.append((source, target))
    return sorted(broken)


def get_backlinks(target_title: str, outgoing: dict[str, list[str]]) -> list[str]:
    """Return all note slugs that link to the given note title."""
    target_slug = slugify(target_title)
    return sorted(
        source for source, targets in outgoing.items()
        if target_slug in targets
    )


def get_orphans(
    outgoing: dict[str, list[str]],
    file_index: dict[str, str],
    map_notes: list[str],
) -> list[str]:
    """Return slugs of notes that have zero incoming links AND are not in any map.

    A note is considered 'in a map' if a map file links to it.
    Self-links do not count as incoming links.
    System files (ops/, self/, templates/, seeds/) are excluded.
    """
    EXCLUDED_PREFIXES = ("ops/", "self/", "templates/", "seeds/", "inbox/", "archive/", ".claude/", "manual/")

    incoming = build_incoming(outgoing)

    # Collect all notes that maps link to
    map_linked: set[str] = set()
    for map_slug in map_notes:
        for target in outgoing.get(map_slug, []):
            map_linked.add(target)

    orphans = []
    for slug, path in file_index.items():
        if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
            continue
        # Exclude root-level files (no directory separator) that aren't notes
        if "/" not in path and not path.startswith("notes/"):
            continue
        # Incoming links excluding self-links
        inbound = [s for s in incoming.get(slug, []) if s != slug]
        if not inbound and slug not in map_linked:
            orphans.append(slug)

    return sorted(orphans)


def get_members(
    map_name: str,
    outgoing: dict[str, list[str]],
    file_index: dict[str, str],
) -> list[str]:
    """Return slugs linked from the named map file."""
    map_slug = slugify(map_name)
    # Allow partial match: 'knowledge-map' matches 'knowledge-map'
    if map_slug not in outgoing:
        # Try suffix match
        matches = [s for s in outgoing if s.endswith(map_slug)]
        if len(matches) == 1:
            map_slug = matches[0]
        elif len(matches) > 1:
            return []  # ambiguous

    targets = outgoing.get(map_slug, [])
    # Only return targets that exist as actual files
    return sorted(t for t in targets if t in file_index)
