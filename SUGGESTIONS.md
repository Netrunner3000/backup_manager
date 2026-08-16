# Backup Control Center — Suggestions & Roadmap

✅ = already implemented. Open items are grouped by effort.

---

## Open backlog (formal todo)

| Item | Notes |
|---|---|
| **Developer ID code signing** | Requires a paid Apple Developer account ($99/yr). Eliminates FDA re-grant after every rebuild and lets launchd launch the app as a reliable fallback. Cannot be done in code alone. |

---

## New suggestions — quick wins

| # | Feature | Status |
|---|---|---|
| A | **Backup pause / resume** | ✅ Aug 2026 |
| B | **Keyboard shortcut Cmd+R to run backup** | Skipped — not needed |
| C | **Tray icon badge on overdue** | ✅ Aug 2026 |
| D | **Restore last log scroll position** | ✅ Aug 2026 |
| E | **Confirm before Quit from tray** | ✅ Aug 2026 |

---

## New suggestions — medium

| # | Feature | Status |
|---|---|---|
| F | **Backup verification spot-check** | Deferred (needs Drive API) |
| G | **Storage quota trend chart** | Deferred (needs SQLite/chart lib) |
| H | **Restore helper** | Deferred (v3 scope) |
| I | **Per-folder backup status** | ✅ Aug 2026 |
| J | **Exclude patterns preview** | ✅ Aug 2026 |
| K | **Backup on USB drive mount** | ✅ Aug 2026 |

---

## New suggestions — bigger

| # | Feature | Status |
|---|---|---|
| L | **S3 / Backblaze B2 as second destination** | Deferred (v3 scope) |
| M | **Email / webhook on backup failure** | Deferred (v3 scope) |
| N | **Backup schedule editor** | ✅ Aug 2026 |
| O | **Quick-backup a single folder** | ✅ Aug 2026 |
| P | **Lab Hub integration — launch from hub** | Deferred (different repo) |

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
