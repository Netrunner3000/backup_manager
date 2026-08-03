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
  and four controls:
  - **▶ Run backup now** — starts the rsync backup immediately.
  - **⚟ Dry run** — previews what rsync would copy without changing any files. Output
    goes to a separate `dryrun_*.log` so it never interferes with backup-detection.
  - **📋 History** — table of the last 15 backup runs (date, start time, duration, status).
  - **■ Stop** — kills the running backup or dry run.
  - Plus three toggles:
    - **Nightly schedule (03:30)** — in-app auto-backup timer. When enabled, checks every
      5 minutes: if past 03:30 and no backup ran since 03:30 today, triggers one.
      Also checks 10 s after launch. **Requires app to be running.**
    - **Wake Mac at 03:25** — `pmset` schedule that wakes the Mac so the timer can fire.
    - **Open at login** — adds/removes the app as a macOS Login Item via System Events
      AppleScript. Keeps the app running in the background so the auto-backup fires.
  - **Notifications** — shows a macOS notification when a real backup finishes (OK or
    errors). Also notifies at each 5-minute poll if the last successful backup is >25 h ago.

- **Backed-up Folders:** add/remove folders from the rsync job (with confirmation before
  removal), edit exclude patterns, see total local size.

- **Tools & Links:** launchers into the backup destination, logs, CloudStorage, iCloud
  Drive, Time Machine settings, in-app docs viewer, each provider's account page, plus:
  - **Google Photos Takeout…** — step-by-step guide for downloading your Google Photos
    library and importing it into the Mac Photos app.
  - **Proton vault status** — checks whether the Proton Drive folder in CloudStorage is
    mounted and accessible.
  - **Time Machine: back up now** — triggers an immediate Time Machine backup.

- **Menu-bar icon** — shows the last backup status in a tooltip; right-click for
  Show, Run Backup Now, and Quit without opening the full window.

- **Dark mode** — automatically matches the system light/dark appearance at launch.

## What it deliberately does NOT do
- It does not reconfigure the proprietary sync engines of iCloud / Google Drive /
  Dropbox / Proton Drive — those stay in their own apps. It has full control only
  over the backup layer we built (the rsync job).
- **iCloud Drive and Proton Drive cannot be added and will never show real cloud quota.**
  Apple publishes no public API for iCloud storage, and Proton publishes none for Proton
  Drive. This is a permanent limitation imposed by both providers, not a missing setup
  step. Their tiles fall back to local disk free space. (Google Drive and Dropbox both
  publish official REST APIs for quota, which is what **Cloud accounts…** uses.)

## How the nightly backup works

The backup is triggered by an in-app timer, not by launchd directly launching the
backup script. This is necessary because macOS 26 (Tahoe) removed `spctl --add` and
blocks unsigned apps from being launched by launchd in non-interactive contexts.

**Flow:**
1. The app runs a 5-minute polling timer.
2. On each tick (and 10 s after launch): if the nightly schedule is enabled, it's past
   03:30, and no backup has started today at or after 03:30 — the backup fires.
3. The backup runs with the app's existing Full Disk Access grant; rsync can read all
   your folders without any extra setup.

**Implication:** the app must be running for the auto-backup to trigger. Leave it open
overnight (it uses no CPU while idle) or set it as a Login Item in System Settings →
General → Login Items so it opens automatically at login.

The launchd job (`com.andreas.gdrive-backup`) remains installed as a best-effort
fallback (it would work if Apple ever re-allows unsigned-app launching from agents),
but the reliable path on macOS 26 is the in-app timer.

## Single-instance guard
Opening a second GUI instance shows a native "Backup Control Center is already open"
alert and brings the existing window to front. The single-instance guard does not
interfere with the `--run-backup` headless mode used by launchd.

## Credentials
OAuth tokens and app credentials are stored in:
```
~/Library/Application Support/Backup Control Center/
```
This location survives `.app` rebuilds. Never stored inside the bundle itself.

## Full Disk Access
The app needs Full Disk Access to let rsync read all your Documents subfolders.
Grant it once in System Settings → Privacy & Security → Full Disk Access → + →
select `/Applications/Backup Control Center.app`.

After each rebuild the code signature changes, so you must re-grant FDA. The app
reminds you if it can't reach the backup destination.

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
Full Disk Access (System Settings → Privacy & Security → Full Disk Access) since the
code signature changes on each build.

## Config it reads/writes
- `~/Documents/lab/_Admin/backup/backup_folders.txt` — backed-up folders
- `~/Documents/lab/_Admin/backup/gdrive_backup_excludes.txt` — rsync exclude patterns
- `~/Documents/lab/_Admin/backup/backup_to_gdrive.sh` — the backup script
- `~/Documents/lab/_Admin/backup/com.andreas.gdrive-backup.plist` — launchd fallback
- `~/Documents/lab/_Admin/backup/logs/` — dated run logs

## Backlog
- Proper Developer ID code signing (removes need for FDA re-grant after each rebuild and
  enables launchd to launch the app directly)
