"""Build a wiki-link adjacency graph from vault markdown files."""

import json
from pathlib import Path

from vault_tools.shared.vault import find_md_files, parse_frontmatter
from vault_tools.shared.wiki_links import extract_links, slugify

GRAPH_CACHE_PATH = "ops/link-graph.json"


def build_graph(vault: Path, verbose: bool = False) -> dict:
    """Scan all vault .md files and build a link adjacency graph.

    Returns a dict with:
      file_index: {slug -> vault-relative path string}
      outgoing:   {slug -> [linked slugs]}
      map_notes:  [slugs of files with type:map]
    """
    md_files = find_md_files(vault)

    # Build file index: slug -> relative path
    file_index: dict[str, str] = {}
    for f in md_files:
        slug = slugify(f.stem)
        file_index[slug] = str(f.relative_to(vault))

    if verbose:
        print(f"  Indexed {len(file_index)} files", flush=True)

    # Scan frontmatter for maps, body for outgoing links
    outgoing: dict[str, list[str]] = {}
    map_notes: list[str] = []

    for f in md_files:
        slug = slugify(f.stem)
        fm = parse_frontmatter(f)

        if fm.get("type") == "map":
            map_notes.append(slug)

        # Scan the whole file, not just the body: tensions store refs in frontmatter.
        all_links = extract_links(f.read_text(encoding="utf-8", errors="replace"))

        outgoing[slug] = [slugify(t) for t in all_links]

    return {
        "file_index": file_index,
        "outgoing": outgoing,
        "map_notes": map_notes,
    }


def save_graph(vault: Path, graph: dict) -> None:
    """Write graph to ops/link-graph.json."""
    from datetime import datetime

    graph["built_at"] = datetime.now().isoformat()
    cache_path = vault / GRAPH_CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")


def load_graph(vault: Path) -> dict | None:
    """Load cached graph if it's newer than the most recently modified .md file."""
    cache_path = vault / GRAPH_CACHE_PATH
    if not cache_path.exists():
        return None

    cache_mtime = cache_path.stat().st_mtime
    md_files = find_md_files(vault)
    if not md_files:
        return None

    newest_md = max(f.stat().st_mtime for f in md_files)
    if cache_mtime < newest_md:
        return None

    return json.loads(cache_path.read_text(encoding="utf-8"))


def get_graph(vault: Path, verbose: bool = False) -> dict:
    """Return graph from cache if fresh, otherwise build live."""
    cached = load_graph(vault)
    if cached:
        if verbose:
            print("  Using cached graph (ops/link-graph.json)", flush=True)
        return cached
    if verbose:
        print("  Building graph live...", flush=True)
    return build_graph(vault, verbose=verbose)
