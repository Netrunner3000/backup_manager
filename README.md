# Backup Control Center

A small PySide6 desktop app to monitor your cloud services and manage the custom
Google Drive backup (the rsync job + launchd schedule in `_Admin/backup/`).

## What it does
Single-screen, scrollable dashboard (no tabs) with four cards:
- **Storage:** Local Disk free space, plus Google Drive / Dropbox mounts with a
  progress bar that turns amber/red as it fills up. Local-disk-only providers
  (Proton Drive, iCloud Drive) are intentionally left out — see below.
  - **Cloud accounts…** — paste in a one-time OAuth app's Client ID/Secret (Google)
    or App Key/Secret (Dropbox), then Connect a mounted account to show its real
    storage quota (used/total) instead of local disk free space.
  - **+ Add account** — monitor a Google Drive / Dropbox account's quota even if
    it isn't mounted locally on this Mac.
- **Google Drive Backup:** last run status, run/stop with live log, and the nightly
  03:30 schedule toggle.
- **Backed-up Folders:** add/remove folders, edit rsync excludes, see total local size.
- **Tools & Links:** one-click launchers into the backup destination, logs,
  CloudStorage, iCloud Drive, Time Machine settings, docs, and each provider's account
  page.

## What it deliberately does NOT do
- It does not reconfigure the proprietary sync engines of iCloud / Google Drive /
  Dropbox / Proton Drive — those stay in their own apps. It has full control only
  over the backup layer we built (the rsync job).
- It does not show account storage quota for Proton Drive or iCloud Drive — neither
  provider publishes a public API for that, for any third-party app. This is a
  permanent limitation, not a missing setup step. (Google Drive and Dropbox do
  publish one, which is what **Cloud accounts…** uses.)

## Run (from source)
```bash
cd ~/Documents/lab/active/backup_manager
uv venv .venv && uv pip install -r requirements.txt   # or python -m venv .venv && pip install -r requirements.txt
source .venv/bin/activate
python main.py
```

## Build as a standalone app
```bash
cd ~/Documents/lab/active/backup_manager
./build_app.sh
```
Builds `Backup Control Center.app` with PyInstaller and installs it into
`/Applications`, so it launches from Spotlight/Finder/Dock like any other app — no
terminal needed. Re-run `build_app.sh` after changing `main.py` to rebuild and
reinstall. `build/` and `dist/` are gitignored (rebuild instead of committing).

## Config it reads/writes
- `~/Documents/lab/_Admin/backup/backup_folders.txt` — the list of backed-up folders
- `~/Documents/lab/_Admin/backup/gdrive_backup_excludes.txt` — exclude patterns
- `~/Documents/lab/_Admin/backup/backup_to_gdrive.sh` — the backup script it runs
- `~/Documents/lab/_Admin/backup/com.andreas.gdrive-backup.plist` — the schedule

## Backlog (not yet started)
- Native macOS notification (success/failure) when a backup finishes, not just the
  in-app log
- Backup history table (last ~10 runs: date, status, duration), not just the latest
- Dry-run preview (`rsync --dry-run`) button before committing to a real run
- Auto-refresh storage tiles on a timer (e.g. every 5 min), not just on manual refresh
- Confirmation dialog before "Remove selected" on a backed-up folder
- Menu-bar companion showing last-backup status without opening the full window
- Consistent light/dark mode — currently force-light everywhere; decide one way and
  apply it fully (this is what caused the QLineEdit dark-mode contrast bug once already)
- Single-instance guard so two copies can't run (and rsync) at once
- Google Photos Takeout → Mac helper + Time Machine trigger
- Proton vault "available offline" check
