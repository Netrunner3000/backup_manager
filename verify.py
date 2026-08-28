"""Spot-check that the backup really holds what the source does.

No Drive API is involved, and none is needed: the backup destination is a local
Google Drive folder, so the copy can be compared against the original with
plain filesystem calls.

The comparison has to reproduce rsync's own rules or it invents failures:

* **excludes** — a file the backup deliberately skips is not missing, so the
  same `gdrive_backup_excludes.txt` patterns are applied here;
* **``--update``** — rsync never overwrites a newer file at the destination, so
  a destination that is newer than the source is correct, not corrupt;
* **``--modify-window=2``** — timestamps only mean anything to the nearest two
  seconds, so anything finer is noise.

Only `stat` is used, never a read. Google Drive streams files on demand, so
hashing the destination would drag the whole backup back down over the network.
Size and timestamp is what can be checked for free, and it catches the failure
that actually matters: a file that never arrived.
"""

from __future__ import annotations

import fnmatch
import random
from dataclasses import dataclass, field
from pathlib import Path

# Matches rsync --modify-window=2 in backup_to_gdrive.sh.
MTIME_TOLERANCE_S = 2

DEFAULT_SAMPLE = 300

MISSING = "missing"
SIZE = "size"
STALE = "stale"
UNREADABLE = "unreadable"


@dataclass
class Finding:
    kind: str
    relative: str
    detail: str

    def __str__(self) -> str:
        return f"{self.relative} — {self.detail}"


@dataclass
class Report:
    checked: int = 0
    matched: int = 0
    symlinks: int = 0
    findings: list[Finding] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)

    def of_kind(self, kind: str) -> list[Finding]:
        return [f for f in self.findings if f.kind == kind]

    @property
    def missing(self) -> list[Finding]:
        return self.of_kind(MISSING)

    @property
    def wrong_size(self) -> list[Finding]:
        return self.of_kind(SIZE)

    @property
    def stale(self) -> list[Finding]:
        return self.of_kind(STALE)

    @property
    def blocked(self) -> list[Finding]:
        return self.of_kind(UNREADABLE)

    @property
    def is_clean(self) -> bool:
        """Stale files are not a fault — they are edits since the last run,
        and an unreadable one is a permissions problem, not a backup problem."""
        return not self.missing and not self.wrong_size

    def summary(self) -> str:
        if not self.checked:
            return "Nothing to check."
        parts = [f"{self.checked} checked", f"{self.matched} match"]
        if self.missing:
            parts.append(f"{len(self.missing)} MISSING")
        if self.wrong_size:
            parts.append(f"{len(self.wrong_size)} wrong size")
        if self.stale:
            parts.append(f"{len(self.stale)} changed since the backup")
        if self.blocked:
            parts.append(f"{len(self.blocked)} unreadable")
        return ", ".join(parts)


def load_excludes(path: Path) -> tuple[str, ...]:
    """The rsync exclude patterns, minus comments and blank lines."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ()
    return tuple(
        line.strip().rstrip("/")
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    )


def is_excluded(relative: Path, patterns: tuple[str, ...]) -> bool:
    """Whether any component of the path matches an exclude pattern.

    rsync applies a bare pattern at every level, and a trailing slash only
    restricts it to directories — which for a file under that directory comes
    to the same thing, since the whole directory is skipped.
    """
    return any(
        fnmatch.fnmatch(part, pattern)
        for part in relative.parts
        for pattern in patterns
    )


def eligible_files(source: Path, patterns: tuple[str, ...]) -> list[Path]:
    """Every backed-up file under `source`, as paths relative to it."""
    found: list[Path] = []
    for path in source.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(source)
        if not is_excluded(relative, patterns):
            found.append(relative)
    return found


def compare(source_file: Path, dest_file: Path, relative: Path) -> Finding | None:
    """One file, source against backup. None means it is fine."""
    # stat, not exists(): exists() answers False for a permission error too,
    # and on a Mac without Full Disk Access to CloudStorage that would report
    # the entire backup as missing.
    try:
        dst = dest_file.stat()
    except FileNotFoundError:
        return Finding(MISSING, str(relative), "not in the backup")
    except PermissionError:
        return Finding(
            UNREADABLE,
            str(relative),
            "could not be read — grant Full Disk Access to check it",
        )

    src = source_file.stat()

    # --update means a newer destination was deliberately left alone, so it is
    # correct even when it differs. Only a source newer than its backup says
    # anything, and what it says is "edited since the last run".
    if src.st_mtime - dst.st_mtime > MTIME_TOLERANCE_S:
        return Finding(
            STALE,
            str(relative),
            "changed since the last backup",
        )
    if dst.st_mtime - src.st_mtime > MTIME_TOLERANCE_S:
        return None  # newer at the destination: rsync kept it on purpose

    if src.st_size != dst.st_size:
        return Finding(
            SIZE,
            str(relative),
            f"{src.st_size} bytes here, {dst.st_size} in the backup",
        )
    return None


def verify(
    folders: list[str],
    source_root: Path,
    dest_root: Path,
    excludes_file: Path,
    *,
    sample: int = DEFAULT_SAMPLE,
    rng: random.Random | None = None,
    log=None,
) -> Report:
    """Compare a random sample of backed-up files against the backup."""
    patterns = load_excludes(excludes_file)
    chooser = rng or random.Random()
    report = Report()

    def say(message: str) -> None:
        if log is not None:
            log(message)

    for folder in folders:
        source = source_root / folder
        if not source.is_dir():
            say(f"Skipping {folder}: not on this Mac.")
            continue

        dest = dest_root / folder
        if not dest.is_dir():
            report.findings.append(
                Finding(MISSING, folder, "the whole folder is absent from the backup")
            )
            say(f"{folder}: MISSING from the backup entirely.")
            continue

        candidates = eligible_files(source, patterns)
        if not candidates:
            say(f"{folder}: nothing to check.")
            continue

        take = min(sample, len(candidates))
        say(f"{folder}: checking {take} of {len(candidates)} files…")

        for relative in chooser.sample(candidates, take):
            try:
                finding = compare(source / relative, dest / relative, relative)
            except OSError as error:
                report.unreadable.append(f"{folder}/{relative}: {error}")
                continue
            report.checked += 1
            if finding is None:
                report.matched += 1
            else:
                finding.relative = f"{folder}/{finding.relative}"
                report.findings.append(finding)
                say(f"  {finding}")

    return report
