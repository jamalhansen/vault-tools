"""Tests for vault-digest builder."""

from pathlib import Path


from vault_tools.digest.builder import (
    BYTE_BUDGET,
    STATUS_LIMIT,
    append_session_log,
    build_digest,
    get_active_threads,
    get_due_reminders,
    get_last_health_check,
    get_pending_counts,
    summarize_status,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestGetActiveThreads:
    def test_extracts_threads(self):
        threads = get_active_threads(FIXTURES)
        assert len(threads) == 3
        names = [t[0] for t in threads]
        assert "SQL Series" in names
        assert "Blog Strategy" in names
        assert "Director Promotion" in names

    def test_returns_empty_for_missing_goals(self, tmp_path):
        assert get_active_threads(tmp_path) == []


class TestGetPendingCounts:
    def test_counts_tension_files(self):
        counts = get_pending_counts(FIXTURES)
        assert counts["tensions"] == 2

    def test_counts_zero_for_missing_dir(self, tmp_path):
        counts = get_pending_counts(tmp_path)
        assert counts["inbox"] == 0

    def test_excludes_resolved_tensions(self):
        # fixtures/ops/tensions/ has one active, one pending, one resolved -- a bare
        # glob would count all three. Only active+pending are genuinely unresolved.
        counts = get_pending_counts(FIXTURES)
        assert counts["tensions"] == 2

    def test_counts_only_pending_observations(self):
        # fixtures/ops/observations/ has one pending, one resolved -- a bare glob
        # would report 2. This is the exact bug that showed "21 pending" in
        # ops/digest.md when only 2 observations were actually pending.
        counts = get_pending_counts(FIXTURES)
        assert counts["observations"] == 1


class TestGetDueReminders:
    def test_returns_overdue_reminders(self):
        # 2020-01-01 is always in the past and within 7-day window (past = due)
        reminders = get_due_reminders(FIXTURES)
        dates = [r[0] for r in reminders]
        assert "2020-01-01" in dates

    def test_excludes_far_future(self):
        reminders = get_due_reminders(FIXTURES)
        dates = [r[0] for r in reminders]
        assert "2099-12-31" not in dates

    def test_returns_empty_for_missing_file(self, tmp_path):
        assert get_due_reminders(tmp_path) == []


class TestGetLastHealthCheck:
    def test_returns_date_of_most_recent_report(self):
        last = get_last_health_check(FIXTURES)
        assert last == "2026-03-01"

    def test_returns_none_for_missing_dir(self, tmp_path):
        assert get_last_health_check(tmp_path) is None


class TestAppendSessionLog:
    def test_creates_file_with_header(self, tmp_path):
        (tmp_path / "ops").mkdir()
        append_session_log(tmp_path, {"inbox": 1, "tensions": 5, "observations": 2}, 10)
        log = (tmp_path / "ops" / "session-log.csv").read_text()
        assert "date,inbox,tensions,observations,orphans" in log
        assert "10" in log

    def test_appends_multiple_rows(self, tmp_path):
        (tmp_path / "ops").mkdir()
        append_session_log(tmp_path, {"inbox": 0, "tensions": 3, "observations": 1}, 5)
        append_session_log(tmp_path, {"inbox": 2, "tensions": 2, "observations": 0}, 4)
        rows = (tmp_path / "ops" / "session-log.csv").read_text().strip().splitlines()
        assert len(rows) == 3  # header + 2 data rows

    def test_handles_none_orphan_count(self, tmp_path):
        (tmp_path / "ops").mkdir()
        append_session_log(tmp_path, {"inbox": 0, "tensions": 1, "observations": 0}, None)
        log = (tmp_path / "ops" / "session-log.csv").read_text()
        assert log.count(",") >= 4  # row written even without orphan count


class TestSummarizeStatus:
    def test_leaves_short_status_untouched(self):
        assert summarize_status("DECIDED 2026-06-11. Execution pending.") == (
            "DECIDED 2026-06-11. Execution pending."
        )

    def test_caps_long_status(self):
        assert len(summarize_status("word " * 200)) <= STATUS_LIMIT

    def test_keeps_the_head_and_drops_the_tail(self):
        status = "ACTIVE. Deployed to prod. " + ("historical detail. " * 40)
        result = summarize_status(status)
        assert result.startswith("ACTIVE. Deployed to prod.")
        assert result.count("historical detail") < 40

    def test_cuts_on_a_sentence_boundary_when_one_is_available(self):
        status = "First sentence here. Second sentence here. " + ("x" * 300)
        assert summarize_status(status).endswith(".")

    def test_marks_a_mid_sentence_cut(self):
        assert summarize_status("supercalifragilistic " * 30).endswith(" ...")

    def test_never_splits_a_word(self):
        result = summarize_status("alpha bravo charlie delta " * 20)
        assert not result.replace(" ...", "").endswith(("alph", "brav", "charli", "delt"))


class TestBuildDigest:
    def test_builds_valid_markdown(self):
        digest = build_digest(FIXTURES)
        assert "# Vault Digest" in digest
        assert "## Active Threads" in digest
        assert "## Pending" in digest
        assert "## Reminders Due" in digest
        assert "## Last Health Check" in digest

    def test_includes_thread_names(self):
        digest = build_digest(FIXTURES)
        assert "SQL Series" in digest
        assert "Director Promotion" in digest

    def test_truncates_thread_status_to_the_limit(self, tmp_path):
        (tmp_path / "self").mkdir()
        long_tail = "and then this happened. " * 60
        (tmp_path / "self" / "goals.md").write_text(
            f"## Active Threads\n- **Aiden** -- ACTIVE. Deployed to prod. {long_tail}\n"
        )
        digest = build_digest(tmp_path)
        thread_line = next(ln for ln in digest.splitlines() if ln.startswith("- **Aiden**"))
        assert len(thread_line) < 260
        assert "ACTIVE. Deployed to prod." in thread_line

    def test_warns_in_the_file_when_over_budget(self, tmp_path):
        (tmp_path / "self").mkdir()
        threads = "".join(f"- **Thread {i}** -- status text here.\n" for i in range(400))
        (tmp_path / "self" / "goals.md").write_text(f"## Active Threads\n{threads}")
        digest = build_digest(tmp_path)
        assert "BUDGET EXCEEDED" in digest

    def test_stays_silent_when_within_budget(self, tmp_path):
        (tmp_path / "self").mkdir()
        (tmp_path / "self" / "goals.md").write_text(
            "## Active Threads\n- **One** -- a short status.\n"
        )
        digest = build_digest(tmp_path)
        assert "BUDGET EXCEEDED" not in digest
        assert len(digest.encode("utf-8")) < BYTE_BUDGET
