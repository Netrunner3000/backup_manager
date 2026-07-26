# Backup Control Center

A PySide6 desktop app to monitor cloud storage and manage the custom Google Drive
backup (the rsync job + launchd schedule in `_Admin/backup/`).

## What it does
Single-screen, scrollable dashboard with four cards:

- **Storage:** Local Disk, Google Drive, and Dropbox tiles — each with a progress bar
  (turns amber/red as it fills) and real account quota via OAuth. Unmounted drives are
  hidden automatically. Duplicate CloudStorage folders for the same account are
  deduplicated. Proton Drive and iCloud Drive are intentionally excluded (see below).
  - **Cloud accounts…** — paste a one-time OAuth Client ID/Secret (Google) or App
    Key/Secret (Dropbox), then Connect each mount to show its real used/total quota.
    Expired tokens show a red "Token expired — reconnect →" link that clears the stale
    token and opens a fresh OAuth flow immediately.
  - **+ Add account** — monitor a Google Drive / Dropbox account's quota even without
    a local mount.

- **Google Drive Backup:** last run timestamp and status (OK / WITH ERRORS), live log,
  manual Run/Stop buttons, and two schedule toggles:
  - **Nightly schedule (03:30)** — launchd job that launches the app headlessly with
    `--run-backup` so it runs in the user's GUI session with full disk access.
  - **Wake Mac at 03:25** — `pmset` schedule that wakes or powers on the Mac before the
    backup so it never misses a run, even after a full shutdown. Requires admin password
    once to set up.

- **Backed-up Folders:** add/remove folders from the rsync job, edit exclude patterns,
  see total local size.

- **Tools & Links:** launchers into the backup destination, logs, CloudStorage, iCloud
  Drive, Time Machine settings, in-app docs viewer, and each provider's account page.

## What it deliberately does NOT do
- It does not reconfigure the proprietary sync engines of iCloud / Google Drive /
  Dropbox / Proton Drive — those stay in their own apps. It has full control only
  over the backup layer we built (the rsync job).
- It does not show account quota for Proton Drive or iCloud Drive — neither provider
  publishes a public API for that. This is a permanent limitation, not a missing setup
  step. (Google Drive and Dropbox do publish one, which is what **Cloud accounts…** uses.)

## Nightly backup — how it works
The launchd job (`com.andreas.gdrive-backup`) calls:
```
/usr/bin/open -a "Backup Control Center" --args --run-backup
```
This launches the app in the user's GUI session (with full TCC/disk access), which
detects `--run-backup`, runs `backup_to_gdrive.sh`, and exits. `/bin/bash` cannot be
granted Full Disk Access directly on macOS 14+ (SIP-protected), which is why the .app
is used as the runner.

If the Mac is sleeping at 03:30 launchd defers the job until the next wake. Enable
**Wake Mac at 03:25** in the app to also cover full-shutdown nights.

## Credentials
OAuth tokens and app credentials are stored in:
```
~/Library/Application Support/Backup Control Center/
```
This location survives `.app` rebuilds. Never stored inside the bundle itself.

## Run (from source)
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
Builds `Backup Control Center.app` with PyInstaller and installs it into `/Applications`.
Re-run after any change to `main.py` or `cloud_quota.py`. After rebuilding, re-grant
Full Disk Access to the new build in System Settings → Privacy & Security → Full Disk
Access (the code signature changes on each build).

## Config it reads/writes
- `~/Documents/lab/_Admin/backup/backup_folders.txt` — backed-up folders
- `~/Documents/lab/_Admin/backup/gdrive_backup_excludes.txt` — rsync exclude patterns
- `~/Documents/lab/_Admin/backup/backup_to_gdrive.sh` — the backup script
- `~/Documents/lab/_Admin/backup/com.andreas.gdrive-backup.plist` — launchd schedule
- `~/Documents/lab/_Admin/backup/logs/` — dated run logs

## Backlog (not yet started)
- Native macOS notification (success/failure) when a backup finishes
- Backup history table (last ~10 runs: date, status, duration)
- Dry-run preview (`rsync --dry-run`) button before committing to a real run
- Auto-refresh storage tiles on a timer (e.g. every 5 min)
- Confirmation dialog before removing a backed-up folder
- Menu-bar companion showing last-backup status without opening the full window
- Consistent light/dark mode (currently force-light throughout)
- Single-instance guard so two copies can't run rsync simultaneously
- Google Photos Takeout → Mac helper + Time Machine trigger
- Proton vault "available offline" check
