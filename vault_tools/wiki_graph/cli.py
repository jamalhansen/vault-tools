"""vg -- wiki-link graph CLI."""

from typing import Annotated

import typer
from local_first_common.tracking import timed_run

from vault_tools.shared.vault import resolve_vault
from vault_tools.wiki_graph.builder import build_graph, get_graph, save_graph
from vault_tools.wiki_graph.queries import get_backlinks, get_broken, get_members, get_orphans

app = typer.Typer(help="Query the vault wiki-link graph.", add_completion=False)
NoCache = Annotated[bool, typer.Option("--no-cache", help="Force live scan")]


@app.callback()
def _root(
    ctx: typer.Context,
    vault: Annotated[str | None, typer.Option("--vault", "-v", help="Path to vault")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show extra detail")] = False,
) -> None:
    """Query the vault wiki-link graph."""
    ctx.obj = {"vault": resolve_vault(vault), "verbose": verbose}


def _graph(ctx: typer.Context, no_cache: bool):
    vault, verbose = ctx.obj["vault"], ctx.obj["verbose"]
    return build_graph(vault, verbose=verbose) if no_cache else get_graph(vault, verbose=verbose)


def _print_slugs(slugs, file_index, empty: str, label: str) -> None:
    if not slugs:
        print(empty)
        return
    for slug in slugs:
        print(f"{slug}  ({file_index.get(slug, '?')})")
    print(f"\nDone. Found: {len(slugs)} {label}")


# No LLM model involved (model=None); each command gives vg a heartbeat on the
# fleet dashboard's activity panel, which vault_tools was invisible to.


@app.command()
def build(ctx: typer.Context) -> None:
    """Build and cache the graph to ops/link-graph.json."""
    vault = ctx.obj["vault"]
    with timed_run("vault-tools", None, source_location=str(vault)) as run:
        graph = build_graph(vault, verbose=ctx.obj["verbose"])
        save_graph(vault, graph)
        note_count = len(graph["file_index"])
        link_count = sum(len(v) for v in graph["outgoing"].values())
        run.item_count = note_count
        print(f"Done. Processed: {note_count} notes, {link_count} links")


@app.command()
def orphans(ctx: typer.Context, no_cache: NoCache = False) -> None:
    """Notes with no incoming links and not in any map."""
    with timed_run("vault-tools", None, source_location=str(ctx.obj["vault"])) as run:
        g = _graph(ctx, no_cache)
        run.item_count = len(g["file_index"])
        _print_slugs(get_orphans(g["outgoing"], g["file_index"], g["map_notes"]), g["file_index"],
                     "No orphans found.", "orphans")


@app.command()
def broken(ctx: typer.Context, no_cache: NoCache = False) -> None:
    """Outgoing links whose target file does not exist."""
    with timed_run("vault-tools", None, source_location=str(ctx.obj["vault"])) as run:
        g = _graph(ctx, no_cache)
        run.item_count = len(g["file_index"])
        pairs = get_broken(g["outgoing"], g["file_index"])
        if not pairs:
            print("No broken links found.")
            return
        for source, target in pairs:
            print(f"{source}  ->  [[{target}]]")
        print(f"\nDone. Found: {len(pairs)} broken links")


@app.command()
def backlinks(
    ctx: typer.Context,
    note: Annotated[str, typer.Argument(help="Note title or slug")],
    no_cache: NoCache = False,
) -> None:
    """Notes that link to a given note."""
    with timed_run("vault-tools", None, source_location=str(ctx.obj["vault"])) as run:
        g = _graph(ctx, no_cache)
        run.item_count = len(g["file_index"])
        _print_slugs(get_backlinks(note, g["outgoing"]), g["file_index"], f"No backlinks found for: {note}", "backlinks")


@app.command()
def members(
    ctx: typer.Context,
    map_name: Annotated[str, typer.Option("--map", "-m", help="Map name (e.g. ai-tools-map)")],
    no_cache: NoCache = False,
) -> None:
    """Notes linked from a map."""
    with timed_run("vault-tools", None, source_location=str(ctx.obj["vault"])) as run:
        g = _graph(ctx, no_cache)
        run.item_count = len(g["file_index"])
        _print_slugs(get_members(map_name, g["outgoing"], g["file_index"]), g["file_index"],
                     f"No members found for map: {map_name}", "members")


if __name__ == "__main__":
    app()
