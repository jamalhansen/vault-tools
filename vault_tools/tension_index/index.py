"""Read and write the tension index file."""

from pathlib import Path

HEADER = "# filename | status | domain | notes | description\n"
INDEX_PATH = "ops/tension-index.md"


def read_index(vault: Path) -> list[str]:
    """Read current index rows (excluding header/comment lines)."""
    path = vault / INDEX_PATH
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip() and not line.startswith("#")]


def write_index(vault: Path, rows: list[str], dry_run: bool = False) -> None:
    """Write header + rows to tension-index.md."""
    content = HEADER + "\n".join(rows) + "\n"
    if dry_run:
        print(content)
        return
    path = vault / INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
