# Backup Control Center — Suggestions & Roadmap

Grouped by effort. Items marked ✅ are already implemented.

---

## Quick wins (< 1 session each)

| # | Feature | Detail |
|---|---|---|
| 1 ✅ | **Dark mode live reload** | `paletteChanged` listener re-themes live. Manual ☀/🌙 toggle in header. |
| 2 | **Keyboard shortcut to run backup** | `Ctrl+R` triggers Run backup now. *(skipped — not needed)* |
| 3 ✅ | **Network trigger status in UI** | "🌐 Network trigger: active/unavailable" label in Backup card. |
| 4 ✅ | **Persist notification cooldown** | `last_overdue_notify` written to `state.json`; survives restarts. |
| 5 ✅ | **Right-click Lab Health → Finder / Terminal** | Context menu on every row. |

---

## Medium (1 session each)

| # | Feature | Detail |
|---|---|---|
| 6 ✅ | **Storage tiles refresh on reconnect** | `QNetworkInformation.reachabilityChanged → Online` triggers `StorageCard.refresh()`. |
| 7 ✅ | **Backup destination health check** | `run_backup()` aborts with a warning if Google Drive mount is missing. |
| 8 ✅ | **Hide to menu bar on close** | Settings dialog (⚙ in header) has "Hide to menu bar on close" toggle; stored in `state.json`. |
| 9 ✅ | **Backup size in History** | Parses rsync `--stats` "Total transferred file size" → Transferred column. |
| 10 ✅ | **Live dark/light toggle** | ☀/🌙 button in header; also auto-updates on system appearance change. |

---

## Bigger (multi-session)

| # | Feature | Detail |
|---|---|---|
| 11 | **Developer ID code signing** | Requires paid Apple Developer account ($99/yr) — cannot be implemented in code alone. Eliminates FDA re-grant after each rebuild. |
| 12 | **In-app Google Drive OAuth flow** | The OAuth browser→localhost flow is already implemented in `cloud_quota.py`. What remains manual is registering your own Google OAuth app (required by Google — can't be bypassed). |
| 13 | **Dropbox in-app OAuth flow** | Same as above — flow exists, Dropbox app registration is a one-time manual step per-user. |
| 14 ✅ | **iCloud local cache tile** | `ICloudTile` shows local iCloud size via `du`. No cloud quota API exists. |
| 15 ✅ | **Time Machine status card** | `TimeMachineCard` shows last backup, idle/running, and Back up now button. |
| 16 ✅ | **Log viewer in History** | 📄 View log button opens the raw rsync log for any selected run. rsync now runs with `--stats --itemize-changes` so logs include per-file changes and transfer totals. |

---

## macOS integration (requires more research)

| # | Feature | Detail |
|---|---|---|
| 17 | **Power Nap backup** | Apple's Power Nap allows certain background tasks while sleeping (iCloud, App Store). Third-party apps cannot opt in directly, but a helper daemon registered via SMAppService might qualify. Needs investigation. |
| 18 | **Shortcuts app integration** | Export a macOS Shortcut that triggers `Backup Control Center --run-backup` so the user can add a backup step to any Shortcuts automation (Focus modes, calendar events, etc.). |
| 19 | **Focus mode awareness** | Suppress notifications during Do Not Disturb / Focus modes using `NSUserNotificationCenter` focus filter API, rather than always sending them. |

---

## Already implemented ✅

| Feature | When |
|---|---|
| Storage tiles (Local, Google Drive, Dropbox) with progress bars | v1 |
| 5-min auto-refresh of storage tiles | v1 |
| Cloud accounts OAuth quota dialog | v1 |
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
| Menu-bar icon (QSystemTrayIcon) | Aug 2026 |
| Dark mode (iOS HIG palette, detected at launch) | Aug 2026 |
| Confirmation dialog before removing folder | Aug 2026 |
| Google Photos Takeout guide in Tools | Aug 2026 |
| Proton vault mount check in Tools | Aug 2026 |
| Lab Health card (project sizes, git status, cleanup) | Aug 2026 |
| Single-instance guard | Aug 2026 |
| Launches maximized | Aug 2026 |
| Dark mode live reload + ☀/🌙 manual toggle | Aug 2026 |
| Network trigger status label in Backup card | Aug 2026 |
| Overdue notification cooldown persisted to state.json | Aug 2026 |
| Right-click Lab Health → Open in Finder / Terminal | Aug 2026 |
| StorageCard refreshes on network reconnect | Aug 2026 |
| Backup destination health check before run | Aug 2026 |
| Settings dialog with hide-to-menu-bar-on-close toggle | Aug 2026 |
| Backup History: Transferred column + per-row log viewer | Aug 2026 |
| rsync --stats + --itemize-changes in all backup runs | Aug 2026 |
| iCloud local cache tile (ICloudTile, du-based) | Aug 2026 |
| Time Machine status card | Aug 2026 |
