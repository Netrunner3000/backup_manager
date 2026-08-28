"""The overdue-backup notification cooldown.

The cooldown is written to `state.json` rather than held in memory, and that is
the whole point: this is a menu-bar app that gets relaunched, and a cooldown
living only in a running process resets every time. Without persistence a login
loop — or just quitting and reopening — would fire the same overdue notice
again and again.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def scratch_state(tmp_path, monkeypatch):
    """Never touch the real state.json: it holds the user's live cooldown."""
    monkeypatch.setattr(main, "_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(main.cloud_quota, "SECRETS_DIR", tmp_path)
    return tmp_path


NOW = datetime(2026, 8, 24, 12, 0, 0)


# ----------------------------------------------------------------------
# The decision
# ----------------------------------------------------------------------
def test_the_first_notice_is_always_allowed():
    assert main.overdue_notice_due(None, NOW) is True


def test_a_second_notice_within_the_hour_is_suppressed():
    assert main.overdue_notice_due(NOW - timedelta(minutes=59), NOW) is False


def test_a_notice_is_allowed_again_after_the_cooldown():
    assert main.overdue_notice_due(NOW - timedelta(minutes=61), NOW) is True


def test_the_boundary_is_inclusive():
    exactly = NOW - timedelta(seconds=main.OVERDUE_COOLDOWN_S)
    assert main.overdue_notice_due(exactly, NOW) is True


# ----------------------------------------------------------------------
# The persistence — the part that actually regressed
# ----------------------------------------------------------------------
def test_nothing_is_remembered_to_begin_with():
    assert main.load_overdue_stamp() is None


def test_the_stamp_survives_a_restart(scratch_state):
    """Reading it back is what a relaunch does."""
    main.save_overdue_stamp(NOW)

    assert (scratch_state / "state.json").exists()
    assert main.load_overdue_stamp() == NOW


def test_the_cooldown_still_applies_after_a_restart():
    """The regression: an in-memory-only cooldown would notify on every launch."""
    main.save_overdue_stamp(NOW - timedelta(minutes=10))

    restored = main.load_overdue_stamp()

    assert main.overdue_notice_due(restored, NOW) is False


def test_saving_the_stamp_keeps_other_settings(scratch_state):
    """state.json is shared — it also holds the webhook URL and scroll position."""
    main._save_state({"webhook_url": "https://ntfy.sh/topic", "log_scroll_pos": 42})

    main.save_overdue_stamp(NOW)

    state = main._load_state()
    assert state["webhook_url"] == "https://ntfy.sh/topic"
    assert state["log_scroll_pos"] == 42


def test_a_corrupt_timestamp_is_ignored_rather_than_crashing(scratch_state):
    main._save_state({"last_overdue_notify": "not a date"})

    assert main.load_overdue_stamp() is None


def test_a_corrupt_state_file_is_survivable(scratch_state):
    (scratch_state / "state.json").write_text("{ this is not json")

    assert main._load_state() == {}
    assert main.load_overdue_stamp() is None
