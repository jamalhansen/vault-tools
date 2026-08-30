"""Vault digest builder -- assembles session summary from vault state."""

import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path


_THREAD_RE = re.compile(r"^- \*\*(.+?)\*\*(?:\s+\[[^\]]*\])?\s+--\s+(.+)$")
_REMINDER_RE = re.compile(r"^- \[ \] (\d{4}-\d{2}-\d{2}):\s+(.+)$")

# The digest is cat'd into session context by session-orient.sh, which has a hard
# output limit. Uncapped thread text pushed that hook to 48KB in July 2026 and the
# whole orientation payload was silently dropped. These two numbers are the guard.
#
# BYTE_BUDGET must stay below what session-orient.sh can spare for the digest, so the
# digest complains before the hook is forced to drop it. As of 2026-07-26 the hook cap
# is 8000 and its other blocks cost ~4200, leaving ~3800. Keep BYTE_BUDGET under that.
STATUS_LIMIT = 120
BYTE_BUDGET = 3600


def summarize_status(status: str, limit: int = STATUS_LIMIT) -> str:
    """Trim a thread or reminder status to its leading sentences, under `limit` chars.

    Lines in goals.md accumulate history at the tail: resolved sub-state, past dates,
    team rosters. The head carries the current state, so truncating from the tail
    keeps what orientation needs and drops the changelog. Full text stays on disk in
    self/goals.md and ops/reminders.md.
    """
    status = status.strip()
    if len(status) <= limit:
        return status

    window = status[:limit]

    # Prefer a sentence boundary, but only if it keeps most of the budget.
    boundary = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
    if boundary >= limit // 2:
        return window[: boundary + 1]

    # Reserve room for the marker so `limit` is a hard ceiling on the result.
    marker = " ..."
    window = status[: limit - len(marker)]
    word_break = window.rfind(" ")
    if word_break <= 0:
        return window
    return window[:word_break].rstrip(",;:") + marker


def get_active_threads(vault: Path) -> list[tuple[str, str]]:
    """Extract active thread names and one-line status from self/goals.md.

    Returns [(thread_name, status_text), ...].
    Returns [] with a warning if the section is missing.
    """
    goals_path = vault / "self" / "goals.md"
    if not goals_path.exists():
        return []

    text = goals_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    in_section = False
    threads = []

    for line in lines:
        if line.strip() == "## Active Threads":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            m = _THREAD_RE.match(line)
            if m:
                threads.append((m.group(1).strip(), m.group(2).strip()))

    return threads


_STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)


def _frontmatter_status(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = _STATUS_RE.search(text[:end])
    return m.group(1) if m else None


def get_pending_counts(vault: Path) -> dict[str, int]:
    """Return counts for inbox/, ops/tensions/, ops/observations/.

    inbox/ has no status field -- everything there is awaiting /reduce, so a bare
    file count is correct. tensions/ and observations/ do have status, and a bare
    glob previously counted resolved/implemented/archived files as "pending" right
    alongside genuinely open ones -- e.g. 21 observations reported when 2 were
    actually pending. Fixed 2026-08-30 (see ops/tool-state-content-discovery.md-style
    postmortem in the digest's own git history for this commit).

    "Unresolved" for a tension means status active OR pending -- both are open, only
    resolved/archived tensions are done. Matches the definition session-orient.sh
    uses for the same count.
    """
    counts = {}

    inbox_path = vault / "inbox"
    counts["inbox"] = len(list(inbox_path.glob("*.md"))) if inbox_path.exists() else 0

    tensions_path = vault / "ops" / "tensions"
    counts["tensions"] = (
        sum(1 for f in tensions_path.glob("*.md") if _frontmatter_status(f) in ("active", "pending"))
        if tensions_path.exists()
        else 0
    )

    observations_path = vault / "ops" / "observations"
    counts["observations"] = (
        sum(1 for f in observations_path.glob("*.md") if _frontmatter_status(f) == "pending")
        if observations_path.exists()
        else 0
    )

    return counts


def get_due_reminders(vault: Path, days: int = 7) -> list[tuple[str, str]]:
    """Return reminders due within `days` days from ops/reminders.md.

    Returns [(date_str, description), ...].
    """
    reminders_path = vault / "ops" / "reminders.md"
    if not reminders_path.exists():
        return []

    today = date.today()
    cutoff = today + timedelta(days=days)
    due = []

    for line in reminders_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _REMINDER_RE.match(line.strip())
        if m:
            try:
                reminder_date = date.fromisoformat(m.group(1))
                if reminder_date <= cutoff:
                    due.append((m.group(1), m.group(2).strip()))
            except ValueError:
                continue

    return sorted(due)


def get_last_health_check(vault: Path) -> str | None:
    """Return the date string of the most recent health report, or None."""
    health_dir = vault / "ops" / "health"
    if not health_dir.exists():
        return None

    reports = sorted(health_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
    if not reports:
        return None

    name = reports[-1].stem
    if len(name) >= 10 and name[:10].count("-") == 2:
        return name[:10]
    return name


SESSION_LOG_PATH = "ops/session-log.csv"
SESSION_LOG_HEADER = ["date", "inbox", "tensions", "observations", "orphans"]


def get_orphan_count(vault: Path) -> int | None:
    """Return cached orphan count from ops/link-graph.json, or None if unavailable."""
    cache_path = vault / "ops" / "link-graph.json"
    if not cache_path.exists():
        return None

    try:
        graph = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Import here to avoid circular imports at module load time
    from vault_tools.wiki_graph.queries import get_orphans

    outgoing = graph.get("outgoing", {})
    file_index = graph.get("file_index", {})
    map_notes = graph.get("map_notes", [])
    return len(get_orphans(outgoing, file_index, map_notes))


def append_session_log(vault: Path, counts: dict[str, int], orphan_count: int | None) -> None:
    """Append one row to ops/session-log.csv."""
    log_path = vault / SESSION_LOG_PATH
    write_header = not log_path.exists()

    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_LOG_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "date": date.today().isoformat(),
            "inbox": counts.get("inbox", 0),
            "tensions": counts.get("tensions", 0),
            "observations": counts.get("observations", 0),
            "orphans": orphan_count if orphan_count is not None else "",
        })


def build_digest(
    vault: Path,
    status_limit: int = STATUS_LIMIT,
    byte_budget: int = BYTE_BUDGET,
) -> str:
    """Assemble the full digest markdown string, capped to `byte_budget`."""
    today = date.today().isoformat()
    threads = get_active_threads(vault)
    counts = get_pending_counts(vault)
    reminders = get_due_reminders(vault)
    last_health = get_last_health_check(vault)

    lines = [
        "# Vault Digest",
        f"generated: {today}",
        "",
        "## Active Threads",
    ]

    if threads:
        for name, status in threads:
            lines.append(f"- **{name}**: {summarize_status(status, status_limit)}")
    else:
        lines.append("(no threads found -- check self/goals.md format)")

    lines += [
        "",
        "## Pending",
        f"- inbox: {counts.get('inbox', 0)} items",
        f"- tensions: {counts.get('tensions', 0)} unresolved",
        f"- observations: {counts.get('observations', 0)} pending",
        "",
        "## Reminders Due",
    ]

    if reminders:
        for d, desc in reminders:
            lines.append(f"- {d}: {summarize_status(desc, status_limit)}")
    else:
        lines.append("(none due within 7 days)")

    lines += [
        "",
        "## Last Health Check",
        last_health if last_health else "(no health reports found)",
    ]

    digest = "\n".join(lines) + "\n"
    size = len(digest.encode("utf-8"))
    if size > byte_budget:
        # Fail loud. A digest that quietly outgrows its budget is how orientation
        # broke last time, so say so in the file itself rather than in a log.
        warning = (
            f"> BUDGET EXCEEDED: {size} bytes against a {byte_budget} budget. "
            f"{len(threads)} active threads. Prune self/goals.md or lower STATUS_LIMIT "
            "-- session-orient.sh will truncate this file before it reaches context."
        )
        lines.insert(2, warning)
        digest = "\n".join(lines) + "\n"

    return digest
