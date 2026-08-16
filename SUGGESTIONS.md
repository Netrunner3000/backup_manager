# Backup Control Center — Suggestions & Roadmap

✅ = already implemented. Open items are grouped by effort.

---

## Open backlog (formal todo)

| Item | Notes |
|---|---|
| **Developer ID code signing** | Requires a paid Apple Developer account ($99/yr). Eliminates FDA re-grant after every rebuild and lets launchd launch the app as a reliable fallback. Cannot be done in code alone. |

---

## New suggestions — quick wins

| # | Feature | Why |
|---|---|---|
| A | **Backup pause / resume** | Add a ⏸ Pause button that sends SIGSTOP to the rsync process and a ▶ Resume that sends SIGCONT. Useful when bandwidth is needed for something else mid-backup. |
| B | **Keyboard shortcut Cmd+R to run backup** | Single line: `QShortcut(QKeySequence("Ctrl+R"), self, self.run_backup)`. Standard for "refresh/run" on macOS. |
| C | **Tray icon badge on overdue** | Change the tray icon to a warning variant (e.g. orange dot overlay) when the backup is overdue, so it's visible at a glance without opening the app. |
| D | **Restore last log scroll position** | Save the scroll position in `state.json` so the log widget re-opens where you left off instead of always at the bottom. |
| E | **Confirm before Quit from tray** | When hide-on-close is enabled, Quit from the tray icon exits silently. Add a one-line confirmation dialog so it's harder to accidentally kill overnight backups. |

---

## New suggestions — medium

| # | Feature | Why |
|---|---|---|
| F | **Backup verification spot-check** | After each successful backup, pick 3–5 random files, compute their checksums locally and in Google Drive (via Drive API), and note any mismatch in the log. Catches silent rsync failures. |
| G | **Storage quota trend chart** | Log used/total quota each refresh to a small SQLite or JSON file; draw a 30-day sparkline in the tile so you can see if you're growing toward a limit. |
| H | **Restore helper** | A "Restore from Drive" button in the Backup card that rsync's a selected folder back from Google Drive to a local staging directory. Uses the same script infrastructure in reverse. |
| I | **Per-folder backup status** | In the Backed-up Folders card, show the last sync timestamp per folder by scanning the log for per-folder "OK: <folder>" lines. Makes it obvious if one folder is always failing. |
| J | **Exclude patterns preview** | In the Excludes dialog, add a "Preview matches" button that runs `find ~/Documents/<folder> -name <pattern>` for each pattern and shows what would be skipped, so you can verify your excludes before the next run. |
| K | **Backup on USB drive mount** | `QFileSystemWatcher` can watch for new mount points. Trigger a backup when a USB drive appears — useful as a secondary local backup destination. |

---

## New suggestions — bigger

| # | Feature | Why |
|---|---|---|
| L | **S3 / Backblaze B2 as second destination** | Add an optional second rsync target (S3-compatible via `rclone`) so there's an offsite copy that isn't Google Drive. The backup script already supports pluggable destinations. |
| M | **Email / webhook on backup failure** | When a backup finishes WITH ERRORS, POST to a configurable webhook URL (Slack, ntfy, Pushover) or send an email via SMTP. Macbook may be offline when you check it. |
| N | **Backup schedule editor** | Currently hardcoded to 03:30. A time-picker in Settings lets you choose any hour. Stores in `state.json`; the polling timer reads it each tick. |
| O | **Quick-backup a single folder** | Right-click any row in Backed-up Folders → "Back up now" runs rsync for just that folder. Useful after a big edit to one project without waiting for the full nightly run. |
| P | **Lab Hub integration — launch from hub** | Register `Backup Control Center` in Lab Hub's launcher list so it appears alongside Sentinel AI, SONAR, etc. Currently only openable from Spotlight or Login Item. |

---

## macOS integration (research needed)

| # | Feature | Detail |
|---|---|---|
| 17 | **Power Nap backup** | Apple's Power Nap wakes certain background tasks during sleep (iCloud, App Store). A helper daemon registered via `SMAppService` might qualify — needs investigation. |
| 18 | **Shortcuts app integration** | Export a macOS Shortcut that triggers `Backup Control Center --run-backup` so the backup can be added to any Shortcuts automation (Focus modes, calendar events, etc.). |
| 19 | **Focus mode notification filter** | Suppress overdue-backup notifications during Do Not Disturb / Focus using the `NSUserNotificationCenter` focus filter API. |

---

## Already implemented ✅

| Feature | When |
|---|---|
| Storage tiles (Local, Google Drive, Dropbox) with progress bars | v1 |
| 5-min auto-refresh of storage tiles | v1 |
| Cloud accounts OAuth quota dialog (Google + Dropbox) | v1 |
| Nightly backup timer (in-app, replaces launchd) | v1 |
| Wake Mac at 03:25 (pmset) toggle | v1 |
| Open at login (Login Item) toggle | v1 |
| Run backup / Stop / Dry run buttons | v1 |
| Backup history table (last 15 runs) | v1 |
| Live log output during backup | v1 |
| Log pre-populated at launch (last 60 lines) | Aug 2026 |
| macOS notification on backup finish | Aug 2026 |
| Overdue-backup notification (>25 h, max once/hr) | Aug 2026 |
| Network-triggered backup on reconnect | Aug 2026 |
| Menu-bar icon (QSystemTrayIcon) with tray menu | Aug 2026 |
| Dark mode (iOS HIG palette, detected at launch) | Aug 2026 |
| Confirmation dialog before removing a backed-up folder | Aug 2026 |
| Google Photos Takeout guide in Tools | Aug 2026 |
| Proton vault mount check in Tools | Aug 2026 |
| Lab Health card (sizes, git status, cleanup) | Aug 2026 |
| Single-instance guard | Aug 2026 |
| Launches maximized | Aug 2026 |
| Dark mode live reload + ☀/🌙 manual toggle | Aug 2026 |
| Network trigger status label in Backup card | Aug 2026 |
| Overdue notification cooldown persisted to state.json | Aug 2026 |
| Right-click Lab Health → Open in Finder / Terminal | Aug 2026 |
| StorageCard refreshes on network reconnect | Aug 2026 |
| Backup destination health check before run | Aug 2026 |
| Settings dialog with hide-to-menu-bar-on-close | Aug 2026 |
| Backup History: Transferred column + per-row log viewer | Aug 2026 |
| rsync --stats + --itemize-changes in all backup runs | Aug 2026 |
| iCloud local cache tile (du-based, no cloud API) | Aug 2026 |
| Time Machine status card | Aug 2026 |
