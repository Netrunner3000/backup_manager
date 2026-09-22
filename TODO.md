# Backup Control Center — TODO

> **Legend** — priority `P0` critical · `P1` high · `P2` normal · `P3` low
> categories `security` `bug` `feature` `performance` `design` `docs` `testing` `infra` `research`
> owner `@me` (needs you — accounts, keys, money, judgement) · `@ai` (Claude can do this)

---

## v2 — current

- [x] `P1` `feature` `@ai` Backup pause / resume via SIGSTOP / SIGCONT
- [x] `P1` `feature` `@ai` Tray icon badge when a backup is overdue
- [x] `P2` `feature` `@ai` Restore last log scroll position on relaunch
- [x] `P2` `feature` `@ai` Per-folder last-synced timestamp in the Folders card
- [x] `P2` `feature` `@ai` Backup triggered on USB volume mount
- [x] `P1` `feature` `@ai` Backup schedule time picker in Settings
- [x] `P2` `testing` `@ai` Regression test for the overdue-notification cooldown persisted in `state.json`
- [x] `P3` `docs` `@ai` Document the `_Admin/backup/` file map in the README rather than only in the table
- [x] `P1` `bug` `@ai` **Backup history only ever showed the day's first run.** Several backups a day (manual re-runs, USB-mount triggers) append to the same daily log file, but `last_backup_info()`/`last_backup_age_hours()`/`last_sync_per_folder()` and the History dialog's `_parse_runs()` all scanned each log as one block of text — so the status shown was always the day's first run's, and the History table listed at most one row per day no matter how many runs actually happened. Fixed with `iter_log_runs()`, which splits a log into per-run blocks on the `===== Backup run started` markers; every caller now iterates runs, not files, so "Last 15 runs" in the History table means runs.
- [x] `P1` `bug` `@ai` **Closing a fullscreen window left a black macOS Space.** The app now leaves fullscreen before the animated hide-to-menu-bar transition, drops the Dock tile only after hiding, and restores a minimized window when reopened.
- [x] `P1` `bug` `@ai` **Backup pre-flight checked the destination instead of the Google Drive mount.** A missing destination is valid because the backup script creates it; Run, Dry run, quick-folder backup, and Preview deletions now test the mounted Drive root and no longer block a healthy first run.

- [x] `P2` `infra` `@ai` **Versioned `v<MAJOR>.<BUILD>`, shown in the app.** The arc
  lives in `VERSION`; the build is `git rev-list --count HEAD`, so it cannot be forgotten.
  `version.py` reads live git from a checkout and a `_build_info.json` stamped by
  `scripts/stamp_version.py` from a frozen bundle, and says `v2.???` rather than guessing
  when it has neither. Shown in the window title, and read by Lab Hub's tile so you can see which
  build its Launch button would open. Lab-wide scheme, same two inputs as the Lab Project
  Monitor.

## v3 — blocked or deferred

- [ ] `P1` `infra` `@me` **Developer ID code signing** — needs a paid Apple Developer account ($99/yr). Removes the Full Disk Access re-grant after every rebuild and makes the launchd fallback reliable. Cannot be done in code.
- [x] `P2` `feature` `@ai` Backup verification spot-check — no Drive API needed after all: the destination is a local Google Drive folder, so `verify.py` compares it directly (honouring the excludes, `--update` and `--modify-window=2`). Tested (`tests/test_verify.py`), but library-only — see the item below.
- [ ] `P2` `feature` `@ai` **Wire `verify.py` into the app.** It has no caller today: no button, no CLI flag, nothing in `main.py` imports it. A **🔍 Verify backup** action (Google Drive Backup card or Tools & Links) or a `--verify` flag would make the spot-check actually reachable.
- [ ] `P2` `feature` `@ai` S3 / Backblaze B2 as a second destination
- [x] `P2` `feature` `@ai` Email or webhook notification on backup failure — webhook shipped (`_fire_webhook`, URL in Settings)
- [ ] `P3` `feature` `@ai` Restore helper — pick a dated log, restore what that run moved
- [x] `P3` `performance` `@ai` Storage quota trend chart — shipped as a QPainter sparkline over persisted samples; needed neither SQLite nor a chart lib
- [ ] `P3` `research` `@ai` Power Nap backup via an `SMAppService` helper daemon — unclear whether a custom daemon qualifies
- [ ] `P3` `feature` `@ai` macOS Shortcuts action that triggers `--run-backup`
