# vault-tools

Three CLI utilities for maintaining Contexta (the Obsidian thinking vault): the wiki-link graph, the vault digest, and the tension index.

## Installation

```bash
cd ~/projects/vault-tools
uv sync
```

Three commands are registered after sync:

| Command | Purpose |
|---------|---------|
| `vg` | Wiki-link graph queries (orphans, broken links, backlinks, map members) |
| `vault-digest` | Build and write the session digest (`ops/digest.md`) |
| `tension-index` | Build and display the flat tension index (`ops/tension-index.md`) |

## vg — Wiki-Link Graph

Builds and queries the vault's wiki-link adjacency graph. The graph is cached to `ops/link-graph.json` and rebuilt on demand.

```bash
# Build and cache the graph
uv run vg build

# Find notes with no incoming links (not in any map)
uv run vg orphans

# Find broken outgoing links (target file doesn't exist)
uv run vg broken

# Find all notes that link to a given note
uv run vg backlinks "structured-prompts-make-llm-output-reusable"

# Find all notes linked from a map
uv run vg members --map ai-tools-map

# Force live scan instead of cache
uv run vg orphans --no-cache

# Use a non-default vault
uv run vg orphans --vault ~/vaults/BrainSync
```

The graph separates `map_notes` (files with `type: map` in frontmatter) from regular notes. Orphan detection excludes notes that are map members even if they have no other incoming links.

**Default vault:** `VAULT_PATH` env var, or `~/vaults/Contexta`.

## vault-digest — Session Digest

Generates a compact markdown summary of current vault state: active threads, pending counts (inbox, tensions, observations), orphan count, and due reminders. Writes to `ops/digest.md` and appends a row to `ops/session-log.csv`.

```bash
# Write digest to ops/digest.md
uv run vault-digest write

# Print to stdout without writing
uv run vault-digest show

# Dry run
uv run vault-digest write --dry-run

# Verbose (shows paths)
uv run vault-digest write --verbose
```

The digest is read at session start by the `session-orient.sh` hook wired into Claude Code.

## tension-index — Tension Index

Scans `ops/tensions/` and builds a flat pipe-separated index at `ops/tension-index.md`. Used by `/rethink` to triage pending tensions.

```bash
# Rebuild index from ops/tensions/
uv run tension-index rebuild

# Dry run (show what would be written)
uv run tension-index rebuild --dry-run

# Print current index
uv run tension-index show
```

Index format: `filename | status | domain | notes | description`

Archived tensions (files ending in `.archived.md`) are included with `status: archived`.

## Module Structure

```
vault_tools/
├── shared/
│   ├── vault.py       -- path resolution, file discovery, frontmatter parsing
│   └── wiki_links.py  -- wiki-link extraction, slugification
├── wiki_graph/
│   ├── builder.py     -- build adjacency graph from vault .md files
│   ├── queries.py     -- orphans, broken links, backlinks, map members
│   └── cli.py         -- vg command
├── digest/
│   ├── builder.py     -- assemble digest from vault state
│   └── cli.py         -- vault-digest command
└── tension_index/
    ├── index.py       -- read/write ops/tension-index.md
    ├── parser.py      -- parse tension files into index rows
    └── cli.py         -- tension-index command
```

## Testing

```bash
uv run pytest
```

Tests use fixture vaults in `tests/fixtures/`.

## Related Tools

| Tool | Purpose |
|------|---------|
| `vault-query` (`~/projects/vault-query`) | Query frontmatter with SQL via DuckDB |
| `vault-log` (`~/projects/vault-log`) | SQLite-backed session log |

See `~/projects/VAULT-TOOLS-SUITE.md` for the full picture of how these three tools relate.
