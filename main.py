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

import sys
import glob
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QProcess
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QTextEdit, QFileDialog, QMessageBox, QDialog,
    QPlainTextEdit, QListWidgetItem, QFrame, QScrollArea, QProgressBar,
    QGraphicsDropShadowEffect, QSizePolicy, QLineEdit, QFormLayout,
)

import cloud_quota

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
# Style
# ----------------------------------------------------------------------------
APP_STYLE = """
QWidget {
    background: #f3f4f7;
    color: #1f2430;
    font-size: 13px;
}
#ScrollArea, #ScrollContent {
    background: #f3f4f7;
    border: none;
}
#AppTitle {
    font-size: 22px;
    font-weight: 700;
    color: #1f2430;
}
#AppSubtitle {
    color: #6b7280;
    font-size: 12px;
}
#Card {
    background: #ffffff;
    border-radius: 14px;
}
#CardTitle {
    font-size: 14px;
    font-weight: 700;
    color: #1f2430;
}
#CardSubtitle {
    color: #6b7280;
    font-size: 11px;
}
#TileName {
    font-weight: 600;
    font-size: 12px;
}
#TileStatus {
    font-size: 11px;
    color: #6b7280;
}
#TileFree {
    font-size: 11px;
    color: #374151;
}
QPushButton {
    background: #2f6fed;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #2860d6;
}
QPushButton:pressed {
    background: #2050ba;
}
QPushButton:disabled {
    background: #c4cbe0;
    color: #f0f1f5;
}
QPushButton[secondary="true"] {
    background: #eef0f6;
    color: #1f2430;
}
QPushButton[secondary="true"]:hover {
    background: #e1e4ee;
}
QPushButton[danger="true"] {
    background: #ef4444;
}
QPushButton[danger="true"]:hover {
    background: #dc2626;
}
QPushButton[link="true"] {
    background: transparent;
    color: #2f6fed;
    text-align: left;
    padding: 6px 4px;
    font-weight: 500;
}
QPushButton[link="true"]:hover {
    color: #1d4ed8;
    background: #eef2ff;
}
QListWidget {
    background: #fafbfc;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 4px;
}
QLineEdit {
    background: #ffffff;
    color: #1f2430;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 5px 8px;
}
QLineEdit:focus {
    border: 1px solid #2f6fed;
}
QDialog {
    background: #f3f4f7;
}
QTextEdit, QPlainTextEdit {
    background: #11151c;
    color: #d7dce3;
    border: none;
    border-radius: 8px;
    font-family: Menlo, monospace;
    font-size: 11px;
}
QProgressBar {
    border: none;
    border-radius: 5px;
    background: #e5e7eb;
    height: 9px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 5px;
    background: #2f6fed;
}
"""


def shadow():
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(18)
    eff.setOffset(0, 3)
    eff.setColor(QColor(0, 0, 0, 30))
    return eff


class Card(QFrame):
    def __init__(self, title=None, subtitle=None):
        super().__init__()
        self.setObjectName("Card")
        self.setGraphicsEffect(shadow())
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(18, 16, 18, 18)
        self.vbox.setSpacing(10)
        if title:
            head = QVBoxLayout()
            head.setSpacing(2)
            t = QLabel(title)
            t.setObjectName("CardTitle")
            head.addWidget(t)
            if subtitle:
                s = QLabel(subtitle)
                s.setObjectName("CardSubtitle")
                head.addWidget(s)
            self.vbox.addLayout(head)

    def body(self, widget_or_layout):
        if isinstance(widget_or_layout, QWidget):
            self.vbox.addWidget(widget_or_layout)
        else:
            self.vbox.addLayout(widget_or_layout)


def secondary_button(text):
    b = QPushButton(text)
    b.setProperty("secondary", True)
    return b


def link_button(text):
    b = QPushButton(text)
    b.setProperty("link", True)
    return b


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


def storage_targets():
    """(name, path, exists) for every mount we can report free space for."""
    rows = [("Local Disk", HOME, True)]
    rows.extend(cloud_services())
    return rows


def disk_usage_for(path):
    """Free/total/used for the filesystem backing `path`, or None if unavailable."""
    try:
        if not Path(path).exists():
            return None
        return shutil.disk_usage(str(path))
    except OSError:
        return None


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
# Storage overview card (free space per mount)
# ----------------------------------------------------------------------------
TILE_WIDTH = 230


class StorageTile(QFrame):
    def __init__(self, name, path, exists, on_connect_request=None):
        super().__init__()
        self.account_key = name
        self.provider = cloud_quota.provider_for_name(name) if exists else None
        self.setFixedWidth(TILE_WIDTH)
        self.setStyleSheet("background: #fafbfc; border-radius: 10px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setObjectName("TileName")
        name_lbl.setToolTip(name)
        fm = name_lbl.fontMetrics()
        avail = TILE_WIDTH - 24 - 16  # margins + status dot
        name_lbl.setText(fm.elidedText(name, Qt.ElideRight, avail))
        top.addWidget(name_lbl)
        top.addStretch()
        dot = "●" if exists else "○"
        status_lbl = QLabel(dot)
        status_lbl.setStyleSheet("color: #16a34a;" if exists else "color: #d1d5db;")
        top.addWidget(status_lbl)
        layout.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        self.detail_lbl = QLabel()
        self.detail_lbl.setObjectName("TileFree")
        self.detail_lbl.setWordWrap(True)
        layout.addWidget(self.detail_lbl)

        if self.provider and exists and not cloud_quota.is_connected(self.account_key):
            connect_btn = link_button("Connect for account quota →")
            connect_btn.setStyleSheet(connect_btn.styleSheet() + "font-size: 10px; padding: 2px 0;")
            if on_connect_request:
                connect_btn.clicked.connect(lambda: on_connect_request(self.account_key, self.provider))
            layout.addWidget(connect_btn)

        self.set_usage(path, exists)

    def _set_bar(self, pct_used):
        self.bar.setValue(pct_used)
        if pct_used >= 90:
            color = "#ef4444"
        elif pct_used >= 70:
            color = "#f59e0b"
        else:
            color = "#2f6fed"
        self.bar.setStyleSheet(
            f"QProgressBar {{ border:none; border-radius:5px; background:#e5e7eb; height:9px; }}"
            f"QProgressBar::chunk {{ border-radius:5px; background:{color}; }}"
        )

    def set_usage(self, path, exists):
        if not exists:
            self.bar.setValue(0)
            self.detail_lbl.setText("not mounted")
            return

        if self.provider and cloud_quota.is_connected(self.account_key):
            try:
                result = cloud_quota.quota(self.account_key)
            except Exception:
                result = None
            if result is not None:
                used, total = result
                if total:
                    self._set_bar(int(used / total * 100))
                    self.detail_lbl.setText(
                        f"{human_size(used)} used of {human_size(total)}  (account quota)"
                    )
                else:
                    self.bar.setValue(0)
                    self.detail_lbl.setText(f"{human_size(used)} used  (unlimited plan)")
                return
            self.detail_lbl.setText("Account quota unavailable — showing local disk:")

        usage = disk_usage_for(path)
        if usage is None:
            self.bar.setValue(0)
            self.detail_lbl.setText("unavailable")
            return
        pct_used = int(usage.used / usage.total * 100) if usage.total else 0
        self._set_bar(pct_used)
        suffix = "  (local disk)" if self.provider else ""
        self.detail_lbl.setText(
            f"{human_size(usage.free)} free of {human_size(usage.total)}{suffix}"
        )


class StorageCard(Card):
    def __init__(self):
        super().__init__()

        header = QHBoxLayout()
        title_lbl = QLabel("Storage")
        title_lbl.setObjectName("CardTitle")
        header.addWidget(title_lbl)
        header.addStretch()
        accounts_btn = secondary_button("☁ Cloud accounts…")
        accounts_btn.clicked.connect(self.open_accounts_dialog)
        header.addWidget(accounts_btn)
        self.vbox.addLayout(header)
        subtitle = QLabel(
            "Local disk free space for every mount, or real account quota once connected")
        subtitle.setObjectName("CardSubtitle")
        self.body(subtitle)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.body(self.grid)
        self.tiles = []
        self.refresh()

    def refresh(self):
        for t in self.tiles:
            t.setParent(None)
        self.tiles = []
        targets = storage_targets()
        cols = 3
        for i, (name, path, exists) in enumerate(targets):
            tile = StorageTile(name, path, exists, on_connect_request=self.connect_account)
            self.grid.addWidget(tile, i // cols, i % cols)
            self.tiles.append(tile)

    def open_accounts_dialog(self):
        CloudAccountsDialog(self, on_change=self.refresh).exec()

    def connect_account(self, account_key, provider):
        dlg = CloudAccountsDialog(self, on_change=self.refresh)
        dlg.exec()


# ----------------------------------------------------------------------------
# Cloud accounts dialog — OAuth app credentials + per-account connect/disconnect
# ----------------------------------------------------------------------------
class ConnectWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, provider, account_key):
        super().__init__()
        self.provider = provider
        self.account_key = account_key

    def run(self):
        try:
            ok, error = cloud_quota.connect(self.provider, self.account_key)
        except Exception as e:
            ok, error = False, str(e)
        self.done.emit(ok, error or "")


class CloudAccountsDialog(QDialog):
    def __init__(self, parent=None, on_change=None):
        super().__init__(parent)
        self.on_change = on_change
        self.worker = None
        self.setWindowTitle("Cloud Accounts")
        self.resize(560, 460)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Connect Google Drive / Dropbox accounts to show their real storage\n"
            "quota instead of local disk free space. Requires a one-time OAuth app\n"
            "(see README) — paste its Client ID/Secret or App Key/Secret below."
        ))

        creds = cloud_quota.load_app_credentials()
        form = QFormLayout()
        self.google_id = QLineEdit(creds.get("google", {}).get("client_id", ""))
        self.google_secret = QLineEdit(creds.get("google", {}).get("client_secret", ""))
        self.google_secret.setEchoMode(QLineEdit.Password)
        self.dropbox_key = QLineEdit(creds.get("dropbox", {}).get("app_key", ""))
        self.dropbox_secret = QLineEdit(creds.get("dropbox", {}).get("app_secret", ""))
        self.dropbox_secret.setEchoMode(QLineEdit.Password)
        form.addRow("Google Client ID:", self.google_id)
        form.addRow("Google Client Secret:", self.google_secret)
        form.addRow("Dropbox App Key:", self.dropbox_key)
        form.addRow("Dropbox App Secret:", self.dropbox_secret)
        layout.addLayout(form)

        save_btn = secondary_button("Save credentials")
        save_btn.clicked.connect(self.save_credentials)
        layout.addWidget(save_btn)

        layout.addWidget(QLabel("\nAccounts:"))
        self.rows_box = QVBoxLayout()
        layout.addLayout(self.rows_box)
        self.populate_rows()

        layout.addStretch()
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("CardSubtitle")
        layout.addWidget(self.status_lbl)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def save_credentials(self):
        cloud_quota.save_app_credentials({
            "google": {
                "client_id": self.google_id.text().strip(),
                "client_secret": self.google_secret.text().strip(),
            },
            "dropbox": {
                "app_key": self.dropbox_key.text().strip(),
                "app_secret": self.dropbox_secret.text().strip(),
            },
        })
        self.status_lbl.setText("Saved.")

    def populate_rows(self):
        while self.rows_box.count():
            item = self.rows_box.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        accounts = [
            (name, cloud_quota.provider_for_name(name))
            for name, _path, exists in cloud_services() if exists
        ]
        accounts = [(n, p) for n, p in accounts if p]
        if not accounts:
            self.rows_box.addWidget(QLabel("No Google Drive / Dropbox mounts found."))
            return

        for name, provider in accounts:
            row = QHBoxLayout()
            lbl = QLabel(name)
            connected = cloud_quota.is_connected(name)
            status = QLabel("● connected" if connected else "○ not connected")
            status.setStyleSheet("color: #16a34a;" if connected else "color: #9ca3af;")
            btn = secondary_button("Disconnect" if connected else "Connect")
            if connected:
                btn.clicked.connect(lambda _, n=name: self.do_disconnect(n))
            else:
                btn.clicked.connect(lambda _, n=name, p=provider: self.do_connect(n, p))
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(status)
            row.addWidget(btn)
            w = QWidget()
            w.setLayout(row)
            self.rows_box.addWidget(w)

    def do_connect(self, account_key, provider):
        self.status_lbl.setText(f"Opening browser to connect {account_key} — sign in and approve access…")
        self.worker = ConnectWorker(provider, account_key)
        self.worker.done.connect(self._connect_finished)
        self.worker.start()

    def _connect_finished(self, ok, error):
        if ok:
            self.status_lbl.setText("Connected.")
        else:
            self.status_lbl.setText(f"Failed: {error}")
        self.populate_rows()
        if self.on_change:
            self.on_change()

    def do_disconnect(self, account_key):
        cloud_quota.disconnect(account_key)
        self.populate_rows()
        if self.on_change:
            self.on_change()


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
        cancel = secondary_button("Cancel")
        cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)

    def save(self):
        EXCLUDES_FILE.write_text(self.edit.toPlainText())
        self.accept()


# ----------------------------------------------------------------------------
# Backup status & schedule card
# ----------------------------------------------------------------------------
class BackupStatusCard(Card):
    def __init__(self):
        super().__init__("Google Drive Backup", "Status, schedule, and manual run")
        self.proc = None

        info, _ = last_backup_info()
        self.status_lbl = QLabel(info)
        self.body(self.status_lbl)

        sched = QHBoxLayout()
        self.sched_lbl = QLabel()
        self.sched_btn = secondary_button("")
        self.sched_btn.clicked.connect(self.toggle_schedule)
        sched.addWidget(self.sched_lbl)
        sched.addStretch()
        sched.addWidget(self.sched_btn)
        self.body(sched)

        runrow = QHBoxLayout()
        self.run_btn = QPushButton("▶  Run backup now")
        self.run_btn.clicked.connect(self.run_backup)
        self.stop_btn = secondary_button("■  Stop")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setEnabled(False)
        runrow.addWidget(self.run_btn)
        runrow.addWidget(self.stop_btn)
        runrow.addStretch()
        self.body(runrow)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        self.body(self.log)

        self.refresh_schedule()

    def refresh_status(self):
        info, _ = last_backup_info()
        self.status_lbl.setText(info)

    def refresh_schedule(self):
        loaded = launchd_loaded()
        self.sched_lbl.setText(
            "🕒 Nightly schedule (03:30): " + ("ENABLED" if loaded else "disabled"))
        self.sched_btn.setText("Disable" if loaded else "Enable")

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
        self.refresh_status()


# ----------------------------------------------------------------------------
# Backed-up folders card
# ----------------------------------------------------------------------------
class FoldersCard(Card):
    def __init__(self):
        super().__init__("Backed-up Folders", "What gets rsync'd to Google Drive")
        self.list = QListWidget()
        self.list.setFixedHeight(120)
        self.body(self.list)

        row = QHBoxLayout()
        add = secondary_button("➕ Add folder")
        add.clicked.connect(self.add_folder)
        rem = secondary_button("➖ Remove selected")
        rem.clicked.connect(self.remove_folder)
        exc = secondary_button("✎ Edit excludes")
        exc.clicked.connect(self.edit_excludes)
        row.addWidget(add)
        row.addWidget(rem)
        row.addWidget(exc)
        row.addStretch()
        self.body(row)

        self.total_lbl = QLabel("Backup set size: calculating…")
        self.total_lbl.setObjectName("CardSubtitle")
        self.body(self.total_lbl)

        self.reload_folders()

    def reload_folders(self):
        self.list.clear()
        for f in read_folders():
            self.list.addItem(QListWidgetItem(f))
        self.total_lbl.setText("Backup set size: calculating…")
        self.worker = SizeWorker(read_folders())
        self.worker.done.connect(lambda sizes, total: self.total_lbl.setText(
            f"Backup set size (local originals): {total}"))
        self.worker.start()

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


# ----------------------------------------------------------------------------
# Tools / quick links card
# ----------------------------------------------------------------------------
class ToolsCard(Card):
    def __init__(self):
        super().__init__("Tools & Links", "Open locations, docs, and provider account pages")
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(2)

        def col(title, items):
            box = QVBoxLayout()
            box.setSpacing(0)
            head = QLabel(title)
            head.setObjectName("TileName")
            box.addWidget(head)
            for text, target in items:
                b = link_button(text)
                if callable(target):
                    b.clicked.connect(target)
                else:
                    b.clicked.connect(lambda _, t=target: run_cmd(["open", str(t)]))
                box.addWidget(b)
            box.addStretch()
            return box

        app_dir = Path(__file__).resolve().parent
        locations = [
            ("Backup destination", DEST_ROOT),
            ("Backup logs", LOG_DIR),
            ("CloudStorage folder", CLOUD_DIR),
            ("iCloud Drive", ICLOUD_DIR),
            ("Time Machine settings",
             lambda: run_cmd(["open", "x-apple.systempreferences:com.apple.Time-Machine-Settings.extension"])),
        ]
        docs = [
            ("App guide (README)", app_dir / "README.md"),
            ("Backup strategy", BACKUP_DIR / "BACKUP_STRATEGY.md"),
            ("Google Drive setup", BACKUP_DIR / "SETUP.md"),
            ("Proton vault guide", BACKUP_DIR / "PROTON_VAULT.md"),
            ("Lab overview", DOCS / "lab" / "README.md"),
        ]
        accounts = [
            ("Google One storage", "https://one.google.com/storage"),
            ("Dropbox plan & usage", "https://www.dropbox.com/account/plan"),
            ("Proton storage dashboard", "https://account.proton.me/u/0/drive"),
            ("iCloud storage settings",
             lambda: run_cmd(["open", "x-apple.systempreferences:com.apple.systempreferences.AppleIDSettings"])),
        ]

        grid.addLayout(col("Open locations", locations), 0, 0)
        grid.addLayout(col("Documentation", docs), 0, 1)
        grid.addLayout(col("Account pages", accounts), 0, 2)
        self.body(grid)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Control Center")
        self.resize(1000, 880)
        self.setMinimumWidth(900)

        scroll = QScrollArea()
        scroll.setObjectName("ScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("ScrollContent")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Backup Control Center")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Dashboard, Google Drive backup, and storage at a glance")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        refresh_btn = secondary_button("🔄 Refresh all")
        refresh_btn.clicked.connect(self.refresh_all)
        header.addWidget(refresh_btn)
        outer.addLayout(header)

        self.storage_card = StorageCard()
        self.backup_card = BackupStatusCard()
        self.folders_card = FoldersCard()
        self.tools_card = ToolsCard()

        outer.addWidget(self.storage_card)
        outer.addWidget(self.backup_card)
        outer.addWidget(self.folders_card)
        outer.addWidget(self.tools_card)
        outer.addStretch()

        scroll.setWidget(content)
        self.setCentralWidget(scroll)

    def refresh_all(self):
        self.storage_card.refresh()
        self.backup_card.refresh_status()
        self.backup_card.refresh_schedule()
        self.folders_card.reload_folders()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
