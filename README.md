# Backup Control Center

A small PySide6 desktop app to monitor your cloud services and manage the custom
Google Drive backup (the rsync job + launchd schedule in `_Admin/backup/`).

## What it does
Single-screen, scrollable dashboard (no tabs) with four cards:
- **Storage:** free space per mount — Local Disk, Google Drive, Dropbox, Proton Drive,
  iCloud Drive — each with a progress bar that turns amber/red as it fills up. This is
  filesystem-level free space (`shutil.disk_usage` on the mount point), not an OAuth
  read of each provider's account quota.
- **Google Drive Backup:** last run status, run/stop with live log, and the nightly
  03:30 schedule toggle.
- **Backed-up Folders:** add/remove folders, edit rsync excludes, see total local size.
- **Tools & Links:** one-click launchers into the backup destination, logs,
  CloudStorage, iCloud Drive, Time Machine settings, docs, and each provider's account
  page (for actual cloud quota, which has no local API).

## What it deliberately does NOT do
iCloud / Google Drive / Dropbox / Proton Drive each run their own proprietary sync
engines with no third-party API (iCloud especially). This app does not try to
reconfigure those — it monitors them and links to their own settings. It has full
control only over the backup layer we built (the rsync job).

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

## Roadmap (v2 ideas)
- Google account quota monitor
- Google Photos Takeout → Mac helper + Time Machine trigger
- Proton vault "available offline" check
- Menu-bar companion + native notifications
- PyInstaller packaging into a standalone .app
