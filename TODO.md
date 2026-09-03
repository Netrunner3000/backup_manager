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
