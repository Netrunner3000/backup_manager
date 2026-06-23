#!/usr/bin/env python3
"""
Backup Control Center
=====================
One place to monitor your cloud services and manage the custom Google Drive backup
(the rsync job + launchd schedule we built). It does NOT try to reconfigure the
proprietary sync engines of iCloud / Google Drive / Dropbox / Proton Drive — those
stay in their own apps. Instead it gives a unified dashboard plus full control of the
backup layer we own, and quick launchers into each service.

Run:  python main.py   (needs PySide6 — see requirements.txt)
"""

import os
import sys
import glob
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QProcess
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QDialog, QPlainTextEdit, QListWidgetItem,
)

# ----------------------------------------------------------------------------
# Paths / config
# ----------------------------------------------------------------------------
HOME = Path.home()
DOCS = HOME / "Documents"
BACKUP_DIR = DOCS / "lab" / "_Admin" / "backup"
SCRIPT = BACKUP_DIR / "backup_to_gdrive.sh"
FOLDERS_FILE = BACKUP_DIR / "backup_folders.txt"
EXCLUDES_FILE = BACKUP_DIR / "gdrive_backup_excludes.txt"
LOG_DIR = BACKUP_DIR / "logs"
PLIST_SRC = BACKUP_DIR / "com.andreas.gdrive-backup.plist"
PLIST_DST = HOME / "Library" / "LaunchAgents" / "com.andreas.gdrive-backup.plist"
LAUNCHD_LABEL = "com.andreas.gdrive-backup"
CLOUD_DIR = HOME / "Library" / "CloudStorage"
ICLOUD_DIR = HOME / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
DEST_ROOT = (CLOUD_DIR / "GoogleDrive-andreas.seel86@gmail.com" /
             "My Drive" / "Backups" / "MacBook" / "Documents")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def human_size(num_bytes):
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def run_cmd(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


def read_folders():
    folders = []
    if FOLDERS_FILE.exists():
        for raw in FOLDERS_FILE.read_text().splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                folders.append(line)
    return folders


def write_folders(folders):
    header = (
        "# Folders under ~/Documents to back up to Google Drive.\n"
        "# One folder (relative to ~/Documents) per line. '#' lines are ignored.\n"
        "# Edited by hand or by the Backup Control Center app.\n"
    )
    FOLDERS_FILE.write_text(header + "\n".join(folders) + "\n")


def du_size(path):
    if not Path(path).exists():
        return "—"
    rc, out, _ = run_cmd(["du", "-sh", str(path)], timeout=120)
    if rc == 0 and out:
        return out.split("\t", 1)[0].strip()
    return "?"


def launchd_loaded():
    rc, out, _ = run_cmd(["launchctl", "list"], timeout=15)
    return LAUNCHD_LABEL in out


def cloud_services():
    rows = []
    if CLOUD_DIR.exists():
        for p in sorted(CLOUD_DIR.iterdir()):
            if p.name.startswith("."):
                continue
            rows.append((p.name, p, p.exists()))
    rows.append(("iCloud Drive", ICLOUD_DIR, ICLOUD_DIR.exists()))
    return rows


def last_backup_info():
    logs = sorted(glob.glob(str(LOG_DIR / "backup_*.log")))
    if not logs:
        return "No backups run yet.", ""
    latest = logs[-1]
    text = Path(latest).read_text(errors="replace") if Path(latest).exists() else ""
    status = "unknown"
    if "finished OK" in text:
        status = "OK"
    elif "WITH ERRORS" in text:
        status = "ERRORS"
    name = Path(latest).stem.replace("backup_", "")
    return f"Last run: {name}  —  {status}", latest


# ----------------------------------------------------------------------------
# Background worker for folder sizes (keeps UI responsive)
# ----------------------------------------------------------------------------
class SizeWorker(QThread):
    done = Signal(dict, str)  # {folder: size}, total_str

    def __init__(self, folders):
        super().__init__()
        self.folders = folders

    def run(self):
        sizes = {}
        total = 0
        for f in self.folders:
            p = DOCS / f
            sizes[f] = du_size(p)
            rc, out, _ = run_cmd(["du", "-sk", str(p)], timeout=120) if p.exists() else (1, "", "")
            if rc == 0 and out:
                try:
                    total += int(out.split("\t", 1)[0]) * 1024
                except ValueError:
                    pass
        self.done.emit(sizes, human_size(total))


# ----------------------------------------------------------------------------
# Dashboard tab
# ----------------------------------------------------------------------------
class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.disk_lbl = QLabel()
        self.disk_lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.disk_lbl)

        self.backup_lbl = QLabel()
        layout.addWidget(self.backup_lbl)

        self.total_lbl = QLabel("Backup set size: calculating…")
        layout.addWidget(self.total_lbl)

        layout.addWidget(QLabel("\nCloud services:"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Service", "Status", "Last changed"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        btn = QPushButton("🔄 Refresh")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)

        self.refresh()

    def refresh(self):
        usage = shutil.disk_usage(str(HOME))
        self.disk_lbl.setText(
            f"💽 Disk: {human_size(usage.free)} free of {human_size(usage.total)}"
        )
        info, _ = last_backup_info()
        self.backup_lbl.setText(f"🗄  {info}")

        rows = cloud_services()
        self.table.setRowCount(len(rows))
        for i, (name, path, exists) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem("● mounted" if exists else "○ not found"))
            changed = ""
            try:
                if exists:
                    changed = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            except OSError:
                changed = ""
            self.table.setItem(i, 2, QTableWidgetItem(changed))

        self.total_lbl.setText("Backup set size: calculating…")
        self.worker = SizeWorker(read_folders())
        self.worker.done.connect(lambda sizes, total: self.total_lbl.setText(
            f"Backup set size (local originals): {total}"))
        self.worker.start()


# ----------------------------------------------------------------------------
# Excludes editor dialog
# ----------------------------------------------------------------------------
class ExcludesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit backup excludes")
        self.resize(560, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Patterns skipped during backup (rsync --exclude-from):"))
        self.edit = QPlainTextEdit()
        if EXCLUDES_FILE.exists():
            self.edit.setPlainText(EXCLUDES_FILE.read_text())
        layout.addWidget(self.edit)
        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)

    def save(self):
        EXCLUDES_FILE.write_text(self.edit.toPlainText())
        self.accept()


# ----------------------------------------------------------------------------
# Google Drive backup tab
# ----------------------------------------------------------------------------
class BackupTab(QWidget):
    def __init__(self):
        super().__init__()
        self.proc = None
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Folders backed up to Google Drive:"))
        self.list = QListWidget()
        layout.addWidget(self.list)

        row = QHBoxLayout()
        add = QPushButton("➕ Add folder")
        add.clicked.connect(self.add_folder)
        rem = QPushButton("➖ Remove selected")
        rem.clicked.connect(self.remove_folder)
        exc = QPushButton("✎ Edit excludes")
        exc.clicked.connect(self.edit_excludes)
        row.addWidget(add)
        row.addWidget(rem)
        row.addWidget(exc)
        row.addStretch()
        layout.addLayout(row)

        # Schedule
        sched = QHBoxLayout()
        self.sched_lbl = QLabel()
        self.sched_btn = QPushButton()
        self.sched_btn.clicked.connect(self.toggle_schedule)
        sched.addWidget(self.sched_lbl)
        sched.addStretch()
        sched.addWidget(self.sched_btn)
        layout.addLayout(sched)

        # Run controls
        runrow = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run backup now")
        self.run_btn.clicked.connect(self.run_backup)
        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setEnabled(False)
        runrow.addWidget(self.run_btn)
        runrow.addWidget(self.stop_btn)
        runrow.addStretch()
        layout.addLayout(runrow)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("font-family: Menlo, monospace; font-size: 11px;")
        layout.addWidget(self.log)

        self.reload_folders()
        self.refresh_schedule()

    # --- folders ---
    def reload_folders(self):
        self.list.clear()
        for f in read_folders():
            self.list.addItem(QListWidgetItem(f))

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Pick a folder under Documents", str(DOCS))
        if not d:
            return
        try:
            rel = Path(d).resolve().relative_to(DOCS.resolve())
        except ValueError:
            QMessageBox.warning(self, "Outside Documents",
                                "Please pick a folder inside ~/Documents.")
            return
        folders = read_folders()
        rel = str(rel)
        if rel in folders:
            return
        folders.append(rel)
        write_folders(folders)
        self.reload_folders()

    def remove_folder(self):
        item = self.list.currentItem()
        if not item:
            return
        folders = [f for f in read_folders() if f != item.text()]
        write_folders(folders)
        self.reload_folders()

    def edit_excludes(self):
        ExcludesDialog(self).exec()

    # --- schedule ---
    def refresh_schedule(self):
        loaded = launchd_loaded()
        self.sched_lbl.setText(
            "🕒 Nightly schedule (03:30): " + ("ENABLED" if loaded else "disabled"))
        self.sched_btn.setText("Disable schedule" if loaded else "Enable schedule")

    def toggle_schedule(self):
        if launchd_loaded():
            run_cmd(["launchctl", "unload", str(PLIST_DST)], timeout=15)
        else:
            if not PLIST_SRC.exists():
                QMessageBox.warning(self, "Missing plist", f"Not found:\n{PLIST_SRC}")
                return
            PLIST_DST.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(PLIST_SRC), str(PLIST_DST))
            run_cmd(["launchctl", "load", str(PLIST_DST)], timeout=15)
        self.refresh_schedule()

    # --- run ---
    def run_backup(self):
        if self.proc is not None:
            return
        self.log.clear()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_output)
        self.proc.finished.connect(self._finished)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.proc.start("/bin/bash", [str(SCRIPT)])

    def stop_backup(self):
        if self.proc is not None:
            self.proc.kill()

    def _read_output(self):
        data = self.proc.readAllStandardOutput().data().decode("utf-8", "replace")
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log.setTextCursor(cursor)
        self.log.insertPlainText(data)

    def _finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.proc = None


# ----------------------------------------------------------------------------
# Tools / launchers tab
# ----------------------------------------------------------------------------
class ToolsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Quick access. The cloud services manage their own syncing in their own "
            "apps — these just open the right place.\n"))

        def open_btn(text, target):
            b = QPushButton(text)
            b.clicked.connect(lambda: run_cmd(["open", str(target)]))
            layout.addWidget(b)

        open_btn("Open backup destination (Google Drive)", DEST_ROOT)
        open_btn("Open backup logs folder", LOG_DIR)
        open_btn("Open CloudStorage (Google / Dropbox / Proton)", CLOUD_DIR)
        open_btn("Open iCloud Drive", ICLOUD_DIR)

        tm = QPushButton("Open Time Machine settings")
        tm.clicked.connect(lambda: run_cmd(
            ["open", "x-apple.systempreferences:com.apple.Time-Machine-Settings.extension"]))
        layout.addWidget(tm)

        layout.addStretch()


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Control Center")
        self.resize(680, 620)
        tabs = QTabWidget()
        tabs.addTab(DashboardTab(), "Dashboard")
        tabs.addTab(BackupTab(), "Google Drive Backup")
        tabs.addTab(ToolsTab(), "Tools")
        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
