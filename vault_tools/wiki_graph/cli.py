"""vg -- wiki-link graph CLI."""

import argparse

from vault_tools.shared.vault import resolve_vault
from vault_tools.wiki_graph.builder import build_graph, get_graph, save_graph
from vault_tools.wiki_graph.queries import get_backlinks, get_broken, get_members, get_orphans


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vg",
        description="Query the vault wiki-link graph.",
    )
    parser.add_argument("--vault", "-v", default=None, help="Path to vault")
    parser.add_argument("--verbose", action="store_true", help="Show extra detail")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="Build and cache the graph to ops/link-graph.json")

    orphans_p = sub.add_parser("orphans", help="Notes with no incoming links and not in any map")
    orphans_p.add_argument("--no-cache", action="store_true", help="Force live scan")

    broken_p = sub.add_parser("broken", help="Outgoing links whose target file does not exist")
    broken_p.add_argument("--no-cache", action="store_true")

    backlinks_p = sub.add_parser("backlinks", help="Notes that link to a given note")
    backlinks_p.add_argument("note", help="Note title or slug")
    backlinks_p.add_argument("--no-cache", action="store_true")

    members_p = sub.add_parser("members", help="Notes linked from a map")
    members_p.add_argument("--map", "-m", required=True, help="Map name (e.g. ai-tools-map)")
    members_p.add_argument("--no-cache", action="store_true")

    args = parser.parse_args()
    vault = resolve_vault(args.vault)

    if args.command == "build":
        graph = build_graph(vault, verbose=args.verbose)
        save_graph(vault, graph)
        note_count = len(graph["file_index"])
        link_count = sum(len(v) for v in graph["outgoing"].values())
        print(f"Done. Processed: {note_count} notes, {link_count} links")
        return

    no_cache = getattr(args, "no_cache", False)
    if no_cache:
        graph = build_graph(vault, verbose=args.verbose)
    else:
        graph = get_graph(vault, verbose=args.verbose)

    outgoing = graph["outgoing"]
    file_index = graph["file_index"]
    map_notes = graph["map_notes"]

    if args.command == "orphans":
        orphans = get_orphans(outgoing, file_index, map_notes)
        if not orphans:
            print("No orphans found.")
        else:
            for slug in orphans:
                path = file_index.get(slug, "?")
                print(f"{slug}  ({path})")
            print(f"\nDone. Found: {len(orphans)} orphans")

    elif args.command == "broken":
        pairs = get_broken(outgoing, file_index)
        if not pairs:
            print("No broken links found.")
        else:
            for source, target in pairs:
                print(f"{source}  ->  [[{target}]]")
            print(f"\nDone. Found: {len(pairs)} broken links")

    elif args.command == "backlinks":
        sources = get_backlinks(args.note, outgoing)
        if not sources:
            print(f"No backlinks found for: {args.note}")
        else:
            for s in sources:
                path = file_index.get(s, "?")
                print(f"{s}  ({path})")
            print(f"\nDone. Found: {len(sources)} backlinks")

    elif args.command == "members":
        members = get_members(args.map, outgoing, file_index)
        if not members:
            print(f"No members found for map: {args.map}")
        else:
            for slug in members:
                path = file_index.get(slug, "?")
                print(f"{slug}  ({path})")
            print(f"\nDone. Found: {len(members)} members")


if __name__ == "__main__":
    main()
