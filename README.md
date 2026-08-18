# Backup Control Center

![Screenshot](docs/screenshot.png)
A PySide6 desktop app to monitor cloud storage and manage the custom Google Drive
backup (the rsync job in `_Admin/backup/`).

## What it does

Single-screen, scrollable dashboard with seven cards plus a menu-bar icon. Launches
maximized. The **☀/🌙** and **⚙** buttons live in the top-right of the header.

---

### Storage
Local Disk, Google Drive, Dropbox, and iCloud Drive tiles — each with a fill bar
(amber at 70 %, red at 90 %). Google Drive and Dropbox show real cloud quota once
connected via OAuth; iCloud shows local cache size only (Apple publishes no quota API).
Unmounted drives are hidden. Duplicate CloudStorage mounts for the same account are
deduplicated. Tiles auto-refresh every 5 minutes **and** immediately when the Mac
reconnects to the network.

- **☁ Cloud accounts…** — enter a Google OAuth Client ID/Secret or Dropbox App
  Key/Secret once; Connect each mount to show real used/total quota. Expired tokens
  show a red "Token expired — reconnect →" link.
- **+ Add account** — monitor a quota-enabled account that has no local mount.
- Connected Google Drive and Dropbox tiles show a **quota sparkline** (last 60 samples)
  drawn below the fill bar so you can see whether usage is growing.

---

### Google Drive Backup
Last run timestamp, status (OK / WITH ERRORS), and a live log pre-populated with the
last 60 lines of the most recent run so status is visible without triggering a new backup.

**Controls:**

| Button | Effect |
|---|---|
| **▶ Run backup now** | Starts the rsync backup immediately (aborts with a warning if Google Drive is not mounted) |
| **⏸ Pause / ▶ Resume** | Suspends or resumes the running rsync process (SIGSTOP/SIGCONT) — useful when bandwidth is needed mid-backup |
| **⚟ Dry run** | Previews what rsync would copy — no files changed; writes to `dryrun_*.log` so it never confuses the auto-backup detector |
| **📋 History** | Last 15 runs: date, start time, duration, bytes transferred, colour-coded status, and a **📄 View log** button for the selected row |
| **■ Stop** | Kills the running backup or dry run |

**Toggles:**

| Toggle | Effect |
|---|---|
| **🕒 Nightly schedule** | Enables the in-app auto-backup timer (time is configurable in ⚙ Settings) |
| **⏰ Wake Mac** | `pmset` wake schedule set 5 min before the backup time — **required** for overnight backups when the Mac sleeps |
| **🚀 Open at login** | Registers the app as a macOS Login Item |
| **🌐 Network trigger** | Label showing whether the network-reconnect trigger loaded successfully |

**Notifications:**
- A macOS notification fires when a real backup finishes (success or errors).
- If the last successful backup is more than 25 hours ago, an overdue warning fires —
  at most once per hour (cooldown persists across restarts) so a long sleep doesn't
  flood Notification Centre.
- The tray icon shows an orange dot overlay when a backup is overdue.

---

### Backed-up Folders
Add or remove folders from the rsync job (confirmation required before removal), edit
rsync exclude patterns, and see the total local size of the backup set.

- Each folder shows its **last-synced timestamp** (scanned from the most recent log).
- **Right-click any folder** → "Back up now" runs rsync for just that one folder — no
  need to wait for the full nightly run after a large edit.
- **Exclude patterns → 🔍 Preview matches** — runs `find` against your backed-up folders
  for each pattern and shows what would be skipped, so you can verify excludes before
  the next run.

---

### Lab Health
Table of every project in `lab/active/` with total size, reclaimable space (`.venv`,
`build`, `dist`, `__pycache__`, etc.), git status, and manifest/`.env` warnings.

- **🧹 Clean up checked** — deletes reclaimable folders after a confirmation dialog
- **🔄 Rescan** — refreshes the table (also runs at launch and on Refresh all)
- **Right-click any row** → Open in Finder or Open in Terminal

Rebuild a cleaned venv with `uv sync` or `pip install -r requirements.txt`.

---

### Time Machine
Last snapshot timestamp, idle/running status, and a **⏱ Back up now** button.
Refreshes every 5 minutes alongside the other cards.

---

### Tools & Links
Quick launchers and helpers:

- **Open locations** — backup destination, logs directory, CloudStorage, iCloud Drive,
  Time Machine settings.
- **Documentation** — in-app viewer for README, Backup Strategy, Google Drive Setup,
  Proton Vault Guide, and Lab Overview.
- **Account pages** — Google One, Dropbox, Proton, iCloud storage pages.
- **Tools** — Google Photos Takeout guide, Proton vault mount check, Time Machine
  back up now (quick shortcut; the full card above has richer status).

---

### Menu-bar icon
Tooltip shows last backup timestamp. Right-click for **Show**, **Run Backup Now**,
and **Quit**. The icon shows an orange dot overlay when the backup is overdue. When
"Hide to menu bar on close" is enabled, **Quit** asks for confirmation so overnight
backups can't be killed accidentally.

---

### Dark mode & theme toggle
Matches system light/dark appearance at launch and updates live when the appearance
changes. The **☀/🌙** button in the header overrides the theme for the current session
without touching system settings.

---

### Settings (⚙)
| Setting | Effect |
|---|---|
| **Hide to menu bar on close** | Closing the window hides the app instead of quitting; use Quit from the menu-bar icon to fully exit |
| **Backup time** | Hour and minute for the nightly schedule (default 03:30). The Wake Mac toggle sets a `pmset` wake 5 minutes before this time. |
| **Webhook URL on failure** | A URL to POST to when a backup finishes with errors. Works with ntfy, Slack incoming webhooks, Pushover, or any JSON-accepting endpoint. Body: `{"text": "…", "message": "…"}`. Leave blank to disable. |

---

## What it deliberately does NOT do
- Does not reconfigure the proprietary sync engines of iCloud, Google Drive, Dropbox,
  or Proton Drive — those stay in their own apps.
- **iCloud Drive and Proton Drive will never show real cloud quota.** No public API
  exists. The iCloud tile shows local cache size only via `du`.
- **Sleep mode suspends everything.** No timer, app, or background process runs while
  the Mac is asleep. Enable **⏰ Wake Mac** so the Mac wakes itself before the scheduled time.

---

## How the nightly backup works

Triggered by an in-app timer, not launchd — required because macOS 26 (Tahoe)
removed `spctl --add` and Gatekeeper blocks unsigned apps in non-interactive launchd
contexts.

**Recommended setup:**
1. Set the backup time in **⚙ Settings** (default 03:30).
2. Enable **🕒 Nightly schedule**.
3. Enable **⏰ Wake Mac** so the Mac powers on 5 minutes before the scheduled time.
4. Enable **🚀 Open at login** so the app is running when the Mac wakes.

**Timer flow:**
1. 5-minute polling timer runs while the app is open.
2. On each tick (and 10 s after launch): if the schedule is enabled, it's past the
   configured time, and no backup has started today at or after that time — the backup fires.
3. rsync runs under the app's Full Disk Access grant.

**Network-triggered backup:** when the Mac comes back online (sleep wake, VPN, outage),
if the last successful backup was more than 12 hours ago and the schedule is enabled,
the app waits 30 seconds for Google Drive to mount then starts a backup automatically.

**USB mount trigger:** when any new volume appears under `/Volumes`, if the last backup
was more than 6 hours ago, a backup starts automatically after a 10-second settle delay.

The launchd job (`com.andreas.gdrive-backup`) remains installed as a best-effort
fallback but the reliable path on macOS 26 is the in-app timer.

---

## Single-instance guard
A second GUI instance shows a native alert and brings the existing window to front.
Does not affect `--run-backup` headless mode.

---

## Credentials & state
All persistent data lives in:
```
~/Library/Application Support/Backup Control Center/
```
| File | Contents |
|---|---|
| `app_credentials.json` | OAuth Client ID/Secret (Google) and App Key/Secret (Dropbox) |
| `tokens.json` | Per-account OAuth refresh tokens |
| `manual_accounts.json` | Accounts added via + Add account |
| `state.json` | Notification cooldown timestamp, settings preferences |

This location survives `.app` rebuilds. Nothing is stored inside the bundle.

---

## Full Disk Access
Required so rsync can read all Documents subfolders.

> System Settings → Privacy & Security → Full Disk Access → **+** →
> select `/Applications/Backup Control Center.app`

**Re-grant after every rebuild** — the ad-hoc code signature changes each time.

---

## Run from source
```bash
cd ~/Documents/lab/active/backup_manager
uv venv .venv && uv pip install -r requirements.txt
source .venv/bin/activate
python main.py
```

## Build as a standalone app
```bash
cd ~/Documents/lab/active/backup_manager
./build_app.sh
```
Builds `Backup Control Center.app` with PyInstaller and installs it to `/Applications`.
Re-run after any change to `main.py` or `cloud_quota.py`, then re-grant Full Disk Access.

`assets/` holds the app icon source — `icon.iconset/`, the compiled `icon.icns`, and
`make_icon.py` which regenerates both.

---

## Config files
| File | Purpose |
|---|---|
| `_Admin/backup/backup_folders.txt` | Folders included in the rsync job |
| `_Admin/backup/gdrive_backup_excludes.txt` | rsync exclude patterns |
| `_Admin/backup/backup_to_gdrive.sh` | The backup script (`DRY_RUN=1` for preview) |
| `_Admin/backup/com.andreas.gdrive-backup.plist` | launchd fallback job |
| `_Admin/backup/logs/backup_YYYY-MM-DD.log` | Dated run logs (include rsync --stats and --itemize-changes output) |
| `_Admin/backup/logs/dryrun_*.log` | Dry-run output (not picked up by backup detection) |

---

## Backlog
- **Developer ID code signing** — eliminates the need to re-grant FDA after each rebuild
  and would let launchd launch the app as a reliable fallback. Requires a paid Apple
  Developer account ($99/yr).

## Suggestions & roadmap
See [SUGGESTIONS.md](SUGGESTIONS.md).
