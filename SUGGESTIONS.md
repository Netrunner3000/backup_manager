# Backup Control Center — Suggestions & Roadmap

Grouped by effort. Items marked ✅ are already implemented.

---

## Quick wins (< 1 session each)

| # | Feature | Detail |
|---|---|---|
| 1 | **Dark mode live reload** | Re-theme without restarting when the user switches system appearance. Listen to `QApplication.paletteChanged` or poll `defaults read -g AppleInterfaceStyle` on each 5-min tick. |
| 2 | **Keyboard shortcut to run backup** | `Ctrl+R` triggers Run backup now. Small, but feels native. |
| 3 | **Show network trigger status in UI** | A small label in the Backup card ("🌐 Network trigger: active") confirms `QNetworkInformation` loaded successfully. Useful for debugging. |
| 4 | **Persist notification cooldown across restarts** | Write `_last_overdue_notify` to `state.json` in `~/Library/Application Support/Backup Control Center/` so the 1-hour cooldown survives a relaunch. |
| 5 | **Right-click Lab Health row → Open in Finder** | `subprocess.run(["open", project_path])` on right-click. One line of code, saves a lot of navigation. |

---

## Medium (1 session each)

| # | Feature | Detail |
|---|---|---|
| 6 | **Storage tiles refresh on network reconnect** | Wire the same `QNetworkInformation.reachabilityChanged → Online` signal to `StorageCard.refresh()` so quotas update immediately after a reconnect, not just on the 5-min timer. |
| 7 | **Backup destination health check** | Before running, verify the Google Drive mount is writable and check available space. Surface a warning in the status label ("⚠ Drive 95% full") rather than letting rsync fail silently. |
| 8 | **Menu-bar only mode** | `--menubar` launch flag (or a preference toggle) starts the app without the main window — just the tray icon. Useful once the app runs as a Login Item and the window is rarely needed. |
| 9 | **Backup size estimate in History** | Parse rsync `--stats` output already in the log to show how many MB were transferred per run in the History table. |
| 10 | **Live dark/light toggle button** | A sun/moon button in the toolbar lets the user flip theme without changing system appearance — useful when running the app on a projector or secondary display. |

---

## Bigger (multi-session)

| # | Feature | Detail |
|---|---|---|
| 11 | **Developer ID code signing** *(existing backlog item)* | Removes the need to re-grant FDA after every rebuild; lets launchd launch the app as a reliable fallback. Requires a paid Apple Developer account ($99/yr). |
| 12 | **In-app Google Drive OAuth flow** | Replace the manual copy-paste of Client ID/Secret with a proper OAuth flow: open browser → receive callback on `localhost` → store token automatically. Removes the setup friction and enables silent token refresh. |
| 13 | **Dropbox in-app OAuth flow** | Same as above for Dropbox (App Key/Secret → browser flow → token). |
| 14 | **iCloud quota via private API** | Apple has no public quota API, but the `du` command on `~/Library/Mobile Documents` gives local iCloud usage. Not a true cloud quota, but better than nothing. |
| 15 | **Time Machine status card** | Show last TM backup time, disk used/total, and a button to trigger a backup now — currently only a quick-launch button exists in Tools. |
| 16 | **Backup diff viewer** | Parse rsync `--itemize-changes` output from a dry run or a real run and display it as a collapsible file tree (new / changed / deleted) instead of raw log text. |

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
