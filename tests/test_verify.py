"""Backup verification.

The rules being reproduced are rsync's, and getting them wrong invents
failures: excluded files are not missing, a newer destination is deliberate
(`--update`), and timestamps only mean anything to two seconds
(`--modify-window=2`).
"""

from __future__ import annotations

import os
import random
import time

import pytest

import verify


@pytest.fixture
def tree(tmp_path):
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    (source / "Docs").mkdir(parents=True)
    (dest / "Docs").mkdir(parents=True)
    excludes = tmp_path / "excludes.txt"
    excludes.write_text("# junk\n.DS_Store\n__pycache__/\n*.pyc\n")
    return source, dest, excludes


def put(root, relative, text="hello", mtime=None):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def run(tree, **kwargs):
    source, dest, excludes = tree
    return verify.verify(
        ["Docs"], source, dest, excludes, rng=random.Random(1), **kwargs
    )


def test_a_matching_file_passes(tree):
    source, dest, _ = tree
    when = time.time() - 500
    put(source, "Docs/a.txt", mtime=when)
    put(dest, "Docs/a.txt", mtime=when)

    report = run(tree)

    assert report.checked == 1
    assert report.matched == 1
    assert report.is_clean


def test_a_file_absent_from_the_backup_is_reported(tree):
    source, _, _ = tree
    put(source, "Docs/gone.txt")

    report = run(tree)

    assert [f.relative for f in report.missing] == ["Docs/gone.txt"]
    assert not report.is_clean


def test_an_excluded_file_is_not_missing(tree):
    """The backup skips it on purpose, so its absence is correct."""
    source, _, _ = tree
    put(source, "Docs/.DS_Store")
    put(source, "Docs/__pycache__/x.pyc")

    report = run(tree)

    assert report.checked == 0
    assert report.is_clean


def test_a_newer_destination_is_left_alone_not_flagged(tree):
    """rsync --update never overwrites a newer file at the destination."""
    source, dest, _ = tree
    now = time.time()
    put(source, "Docs/a.txt", text="old", mtime=now - 600)
    put(dest, "Docs/a.txt", text="a much longer newer version", mtime=now)

    report = run(tree)

    assert report.is_clean, "a deliberately newer backup must not read as corrupt"
    assert report.matched == 1


def test_a_source_edited_since_the_backup_is_flagged_but_not_a_fault(tree):
    source, dest, _ = tree
    now = time.time()
    put(dest, "Docs/a.txt", mtime=now - 600)
    put(source, "Docs/a.txt", text="edited", mtime=now)

    report = run(tree)

    assert len(report.stale) == 1
    assert report.is_clean, "an edit since the last run is not a backup failure"


def test_a_size_mismatch_at_the_same_time_is_a_fault(tree):
    """Same timestamp, different size: the copy is wrong."""
    source, dest, _ = tree
    when = time.time() - 500
    put(source, "Docs/a.txt", text="the full contents", mtime=when)
    put(dest, "Docs/a.txt", text="trunc", mtime=when)

    report = run(tree)

    assert len(report.wrong_size) == 1
    assert not report.is_clean


def test_timestamps_within_the_modify_window_still_match(tree):
    source, dest, _ = tree
    when = time.time() - 500
    put(source, "Docs/a.txt", mtime=when)
    put(dest, "Docs/a.txt", mtime=when + verify.MTIME_TOLERANCE_S - 0.5)

    report = run(tree)

    assert report.matched == 1


def test_a_whole_folder_missing_is_reported_once(tree):
    source, dest, excludes = tree
    put(source, "Docs/a.txt")
    (dest / "Docs").rmdir()

    report = run(tree)

    assert len(report.missing) == 1
    assert "folder" in report.missing[0].detail


def test_an_unreadable_backup_is_not_called_missing(tree, monkeypatch):
    """Path.exists() answers False for permission denied as well, which on a
    Mac without Full Disk Access would report the whole backup as gone."""
    source, dest, _ = tree
    put(source, "Docs/a.txt")
    put(dest, "Docs/a.txt")

    # Only this one file: patching stat wholesale also breaks the directory
    # checks, and the test would pass for the wrong reason.
    from pathlib import Path

    target = dest / "Docs" / "a.txt"
    real_stat = Path.stat

    def denied(self, *args, **kwargs):
        if self == target:
            raise PermissionError(13, "Operation not permitted")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", denied)

    report = run(tree)

    assert not report.missing, "a permissions problem is not a missing file"
    assert len(report.blocked) == 1
    assert report.is_clean


def test_the_sample_is_capped(tree):
    source, _, _ = tree
    for index in range(30):
        put(source, f"Docs/f{index}.txt")

    report = run(tree, sample=5)

    assert report.checked == 5


def test_symlinks_are_not_compared(tree):
    """rsync copies them as links; following them would compare the target."""
    source, dest, _ = tree
    put(source, "Docs/real.txt")
    put(dest, "Docs/real.txt")
    (source / "Docs" / "link.txt").symlink_to(source / "Docs" / "real.txt")

    report = run(tree)

    assert report.checked == 1
