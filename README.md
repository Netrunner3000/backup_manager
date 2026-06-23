# Backup Control Center

A small PySide6 desktop app to monitor your cloud services and manage the custom
Google Drive backup (the rsync job + launchd schedule in `_Admin/backup/`).

## What it does
- **Dashboard:** free disk space, last backup status, and a list of your cloud
  services (Google Drive, Dropbox, Proton Drive, iCloud) with mount status — plus the
  total size of your local backup set.
- **Google Drive Backup tab:** add/remove the folders that get backed up, edit the
  exclude rules, run the backup now (with live log) or stop it, and enable/disable the
  nightly 03:30 schedule.
- **Tools tab:** one-click launchers into the backup destination, logs, CloudStorage,
  iCloud Drive, and Time Machine settings.

## What it deliberately does NOT do
iCloud / Google Drive / Dropbox / Proton Drive each run their own proprietary sync
engines with no third-party API (iCloud especially). This app does not try to
reconfigure those — it monitors them and links to their own settings. It has full
control only over the backup layer we built (the rsync job).

## Run
```bash
cd ~/Documents/lab/active/backup_manager
uv venv .venv && uv pip install -r requirements.txt   # or python -m venv .venv && pip install -r requirements.txt
source .venv/bin/activate
python main.py
```

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
