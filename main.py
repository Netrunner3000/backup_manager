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
import fcntl
import glob
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Headless mode: launchd calls the .app with --run-backup instead of /bin/bash directly.
# This lets the app's FDA grant cover the subprocess, bypassing the /bin/bash TCC block.
if "--run-backup" in sys.argv:
    _script = Path.home() / "Documents" / "lab" / "_Admin" / "backup" / "backup_to_gdrive.sh"
    sys.exit(subprocess.run(["/bin/bash", str(_script)]).returncode)

from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer, QProcessEnvironment, QEvent
from PySide6.QtGui import QTextCursor, QColor, QIcon, QPixmap
from PySide6.QtNetwork import QNetworkInformation
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QTextEdit, QTextBrowser, QFileDialog, QMessageBox, QDialog,
    QPlainTextEdit, QListWidgetItem, QFrame, QScrollArea, QProgressBar,
    QGraphicsDropShadowEffect, QSizePolicy, QLineEdit, QFormLayout, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSystemTrayIcon, QMenu,
)

import cloud_quota

# Set by main() before creating QApplication; used by widgets that need to
# apply different inline styles for dark/light mode.
_DARK: bool = False

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
LAB_ACTIVE = DOCS / "lab" / "active"
# Same disposable-junk names as gdrive_backup_excludes.txt — if it's not worth
# backing up, it's not worth keeping locally once the project is idle either.
DISPOSABLE_DIR_NAMES = {
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", ".cache", "dist", "build",
}


# ----------------------------------------------------------------------------
# Style (dynamic — built once at startup based on system dark/light mode)
# ----------------------------------------------------------------------------
def build_app_style(dark: bool) -> str:
    # iOS / macOS Human Interface Guideline palette
    if dark:
        page     = "#1C1C1E"   # systemBackground (dark)
        card     = "#2C2C2E"   # secondarySystemBackground (dark)
        card_bdr = "#38383A"   # separator (dark)
        text     = "#FFFFFF"   # label (dark)
        sec      = "#98989D"   # secondaryLabel (dark)
        tile_bg  = "#3A3A3C"   # tertiarySystemFill (dark)
        tile_bdr = "#48484A"
        acc      = "#0A84FF"   # systemBlue (dark)
        acc_hov  = "#0070E0"
        acc_prs  = "#005EC7"
        sec_bg   = "#3A3A3C"   # systemFill (dark)
        sec_hov  = "#48484A"
        inp_bg   = "#2C2C2E"
        inp_bdr  = "#48484A"
        inp_foc  = "#0A84FF"
        dis_bg   = "#2C2C2E"
        dis_fg   = "#48484A"
        link_clr = "#0A84FF"
        link_hov = "#0A2A4A"
        danger   = "#FF453A"   # systemRed (dark)
        danger_h = "#D93830"
        list_bg  = "#2C2C2E"
        list_bdr = "#38383A"
        sel_bg   = "#0A84FF33"
        hdr_bg   = "#3A3A3C"
        menu_bg  = "#2C2C2E"
        menu_bdr = "#38383A"
    else:
        page     = "#F2F2F7"   # systemBackground (light)
        card     = "#FFFFFF"   # secondarySystemBackground (light)
        card_bdr = "#C6C6C8"   # separator (light)
        text     = "#1C1C1E"   # label (light)
        sec      = "#636366"   # secondaryLabel (light)
        tile_bg  = "#F9F9FB"   # tertiarySystemFill (light)
        tile_bdr = "#E5E5EA"
        acc      = "#007AFF"   # systemBlue (light)
        acc_hov  = "#006BE0"
        acc_prs  = "#005BC7"
        sec_bg   = "#E5E5EA"   # systemFill (light)
        sec_hov  = "#D1D1D6"
        inp_bg   = "#FFFFFF"
        inp_bdr  = "#C6C6C8"
        inp_foc  = "#007AFF"
        dis_bg   = "#E5E5EA"
        dis_fg   = "#AEAEB2"
        link_clr = "#007AFF"
        link_hov = "#EFF6FF"
        danger   = "#FF3B30"   # systemRed (light)
        danger_h = "#E0342A"
        list_bg  = "#FFFFFF"
        list_bdr = "#E5E5EA"
        sel_bg   = "#007AFF22"
        hdr_bg   = "#F2F2F7"
        menu_bg  = "#FFFFFF"
        menu_bdr = "#C6C6C8"

    return f"""
/* ── Base: colour + font only — NO background.
   Setting background here would paint every child widget with the page
   colour, creating visible dark boxes inside lighter cards. Instead each
   container sets its own background explicitly. ── */
QWidget {{
    color: {text};
    font-size: 13px;
}}

/* ── Page background — only on outer containers ── */
QMainWindow, QScrollArea, QAbstractScrollArea,
#ScrollArea, #ScrollContent, QDialog {{
    background: {page};
    border: none;
}}

/* ── Labels and other passive widgets: transparent
   so the parent container's background shows through ── */
QLabel {{
    background: transparent;
    color: {text};
}}

/* ── App header ─────────────────────────────────── */
#AppTitle {{
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
#AppSubtitle {{
    color: {sec};
    font-size: 12px;
}}

/* ── Cards ──────────────────────────────────────── */
#Card {{
    background: {card};
    border-radius: 12px;
    border: 1px solid {card_bdr};
}}
#CardTitle {{
    font-size: 13px;
    font-weight: 600;
    letter-spacing: -0.1px;
}}
#CardSubtitle {{
    color: {sec};
    font-size: 11px;
}}

/* ── Storage tiles ──────────────────────────────── */
#StorageTile {{
    background: {tile_bg};
    border-radius: 10px;
    border: 1px solid {tile_bdr};
}}
#TileName {{
    font-weight: 600;
    font-size: 12px;
}}
#TileAccount {{
    font-size: 10px;
    color: {sec};
}}
#TileStatus {{
    font-size: 11px;
    color: {sec};
}}
#TileFree {{
    font-size: 11px;
    color: {sec};
}}

/* ── Buttons — primary ──────────────────────────── */
QPushButton {{
    background: {acc};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background: {acc_hov};
}}
QPushButton:pressed {{
    background: {acc_prs};
}}
QPushButton:disabled {{
    background: {dis_bg};
    color: {dis_fg};
}}

/* ── Buttons — secondary ────────────────────────── */
QPushButton[secondary="true"] {{
    background: {sec_bg};
    color: {text};
    border: none;
}}
QPushButton[secondary="true"]:hover {{
    background: {sec_hov};
}}
QPushButton[secondary="true"]:disabled {{
    background: {dis_bg};
    color: {dis_fg};
}}

/* ── Buttons — danger ───────────────────────────── */
QPushButton[danger="true"] {{
    background: {danger};
    color: white;
}}
QPushButton[danger="true"]:hover {{
    background: {danger_h};
}}

/* ── Buttons — link / inline ────────────────────── */
QPushButton[link="true"] {{
    background: transparent;
    color: {link_clr};
    text-align: left;
    padding: 4px 2px;
    font-weight: 500;
    border: none;
}}
QPushButton[link="true"]:hover {{
    color: {acc_hov};
    background: {link_hov};
    border-radius: 4px;
}}

/* ── Lists & tables ─────────────────────────────── */
QListWidget {{
    background: {list_bg};
    border: 1px solid {list_bdr};
    border-radius: 8px;
    padding: 4px;
    outline: 0;
}}
QListWidget::item {{
    border-radius: 5px;
    padding: 3px 6px;
}}
QListWidget::item:selected {{
    background: {sel_bg};
    color: {text};
}}
QTableWidget {{
    background: {list_bg};
    border: 1px solid {list_bdr};
    border-radius: 8px;
    gridline-color: {list_bdr};
    outline: 0;
}}
QTableWidget::item:selected {{
    background: {sel_bg};
    color: {text};
}}
QHeaderView::section {{
    background: {hdr_bg};
    color: {sec};
    border: none;
    border-bottom: 1px solid {list_bdr};
    padding: 5px 10px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

/* ── Inputs ─────────────────────────────────────── */
QLineEdit {{
    background: {inp_bg};
    color: {text};
    border: 1px solid {inp_bdr};
    border-radius: 8px;
    padding: 6px 10px;
}}
QLineEdit:focus {{
    border: 1.5px solid {inp_foc};
}}

/* ── Dialogs ────────────────────────────────────── */
QDialog {{
    background: {page};
}}

/* ── Log / code output (always dark terminal) ───── */
QTextEdit, QPlainTextEdit {{
    background: #0D1117;
    color: #C9D1D9;
    border: 1px solid {"#30363D" if dark else "#D0D7DE"};
    border-radius: 8px;
    font-family: Menlo, "SF Mono", Consolas, monospace;
    font-size: 11px;
    padding: 4px;
}}

/* ── Progress bars ──────────────────────────────── */
QProgressBar {{
    border: none;
    border-radius: 4px;
    background: {tile_bdr};
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background: {acc};
}}

/* ── Menus ──────────────────────────────────────── */
QMenu {{
    background: {menu_bg};
    color: {text};
    border: 1px solid {menu_bdr};
    border-radius: 8px;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 0px;
}}
QMenu::item:selected {{
    background: {acc};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {menu_bdr};
    margin: 3px 8px;
}}

/* ── Scroll bars (subtle) ───────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {"#48484A" if dark else "#C6C6C8"};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {"#48484A" if dark else "#C6C6C8"};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def shadow():
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(12)
    eff.setOffset(0, 2)
    eff.setColor(QColor(0, 0, 0, 18))
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


def wake_schedule_active():
    _, out, _ = run_cmd(["pmset", "-g", "sched"], timeout=10)
    return "03:25" in out


def set_wake_schedule(enable):
    if enable:
        cmd = "pmset repeat wakeorpoweron MTWRFSU 03:25:00"
    else:
        cmd = "pmset repeat cancel"
    rc, _, err = run_cmd([
        "osascript", "-e",
        f'do shell script "{cmd}" with administrator privileges',
    ], timeout=60)
    return rc == 0, err


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
    """(name, path, exists) for Local Disk plus mounts that can show real account
    quota (Google Drive, Dropbox). Proton Drive / iCloud Drive have no public quota
    API, so showing them here would just repeat the Local Disk number — they're
    left out rather than displayed as a misleading duplicate.
    Deduplicates by base account email — keeps the shortest (cleanest) folder name
    when Google Drive creates multiple mounts for the same account."""
    rows = [("Local Disk", HOME, True)]
    seen = {}  # base_email -> (name, path, exists)
    for name, path, exists in cloud_services():
        if not cloud_quota.provider_for_name(name):
            continue
        _, account = split_tile_name(name)
        base = re.sub(r'\s+\(\d{2}-\d{2}-\d{4}.*\)$', '', account).strip()
        key = (cloud_quota.provider_for_name(name), base)
        if key not in seen or len(name) < len(seen[key][0]):
            seen[key] = (name, path, exists)
    rows.extend(seen.values())
    return rows


def split_tile_name(name):
    """Split a CloudStorage folder name into (provider, account) for display."""
    if name.startswith("GoogleDrive-"):
        return "Google Drive", name[len("GoogleDrive-"):]
    if name.startswith("ProtonDrive-"):
        account = name[len("ProtonDrive-"):]
        account = re.sub(r"-folder\b", "", account)
        return "Proton Drive", account
    if name.startswith("Dropbox"):
        account = name[len("Dropbox"):].strip()
        return "Dropbox", account
    return name, ""


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
    match = re.search(r"\[([\d-]{10} [\d:]{8})\]\s+===== Backup run finished", text)
    timestamp = match.group(1) if match else Path(latest).stem.replace("backup_", "")
    return f"Last run: {timestamp}  —  {status}", latest


def last_backup_age_hours() -> float | None:
    """Hours since the last successful backup finished, or None if no record."""
    logs = sorted(glob.glob(str(LOG_DIR / "backup_*.log")))
    for log_path in reversed(logs):
        text = Path(log_path).read_text(errors="replace")
        m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+===== Backup run finished OK", text)
        if m:
            try:
                t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                return (datetime.now() - t).total_seconds() / 3600
            except ValueError:
                pass
    return None


def _system_dark_mode() -> bool:
    rc, out, _ = run_cmd(["defaults", "read", "-g", "AppleInterfaceStyle"], timeout=5)
    return out.strip().lower() == "dark"


def _notify(title: str, message: str, subtitle: str = "") -> None:
    sub = f'subtitle "{subtitle}" ' if subtitle else ""
    subprocess.Popen(
        ["osascript", "-e",
         f'display notification "{message}" with title "{title}" {sub}'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def is_login_item() -> bool:
    rc, out, _ = run_cmd(
        ["osascript", "-e",
         'tell application "System Events" to return (name of login items) contains "Backup Control Center"'],
        timeout=10,
    )
    return out.strip().lower() == "true"


def set_login_item(enable: bool) -> tuple:
    if enable:
        script = ('tell application "System Events" to make new login item at end '
                  'with properties {path:"/Applications/Backup Control Center.app", hidden:false}')
    else:
        script = 'tell application "System Events" to delete login item "Backup Control Center"'
    rc, _, err = run_cmd(["osascript", "-e", script], timeout=10)
    return rc == 0, err


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


class LabHealthWorker(QThread):
    """Scans lab/active/<project> for disk hogs, git hygiene, and missing manifests."""
    done = Signal(list)  # list of row dicts

    def run(self):
        rows = []
        if LAB_ACTIVE.exists():
            for proj in sorted(LAB_ACTIVE.iterdir()):
                if proj.is_dir() and not proj.name.startswith("."):
                    rows.append(self._scan_project(proj))
        self.done.emit(rows)

    @classmethod
    def _scan_project(cls, proj):
        total_kb = cls._size_kb(proj)
        reclaim_items = [(p, cls._size_kb(p)) for p in cls._find_disposable(proj)]
        reclaim_kb = sum(kb for _, kb in reclaim_items)

        has_git = (proj / ".git").is_dir()
        uncommitted, last_commit = 0, "—"
        if has_git:
            _, out, _ = run_cmd(["git", "-C", str(proj), "status", "--porcelain"], timeout=20)
            uncommitted = len([l for l in out.splitlines() if l.strip()])
            _, out2, _ = run_cmd(
                ["git", "-C", str(proj), "log", "-1", "--format=%ad", "--date=short"], timeout=20)
            last_commit = out2.strip() or "—"

        has_manifest = (proj / "requirements.txt").exists() or (proj / "pyproject.toml").exists()

        env_flag = ""
        if (proj / ".env").exists():
            if has_git:
                rc, _, _ = run_cmd(["git", "-C", str(proj), "check-ignore", "-q", ".env"], timeout=10)
                env_flag = "" if rc == 0 else "⚠️ .env not git-ignored"
            else:
                env_flag = ".env present (no git repo to check)"

        return {
            "name": proj.name,
            "total_kb": total_kb,
            "reclaim_kb": reclaim_kb,
            "reclaim_items": reclaim_items,
            "has_git": has_git,
            "uncommitted": uncommitted,
            "last_commit": last_commit,
            "has_manifest": has_manifest,
            "env_flag": env_flag,
        }

    @staticmethod
    def _size_kb(path):
        rc, out, _ = run_cmd(["du", "-sk", str(path)], timeout=120)
        if rc == 0 and out:
            try:
                return int(out.split("\t", 1)[0])
            except ValueError:
                pass
        return 0

    @staticmethod
    def _find_disposable(proj):
        """Top-most matching dirs only (-prune) so nested __pycache__ inside a
        .venv isn't counted twice, and every match is independently rm-able."""
        names = sorted(DISPOSABLE_DIR_NAMES)
        name_expr = []
        for i, n in enumerate(names):
            if i:
                name_expr.append("-o")
            name_expr += ["-name", n]
        args = ["find", str(proj), "-mindepth", "1", "-type", "d",
                "(", *name_expr, ")", "-prune", "-print"]
        rc, out, _ = run_cmd(args, timeout=60)
        if rc != 0:
            return []
        return [Path(p) for p in out.splitlines() if p.strip()]


# ----------------------------------------------------------------------------
# Storage overview card (free space per mount)
# ----------------------------------------------------------------------------
TILE_WIDTH = 230


class StorageTile(QFrame):
    def __init__(self, name, path, exists, on_connect_request=None,
                 provider_override=None, display_account=None, quota_only=False):
        super().__init__()
        self.account_key = name
        self.quota_only = quota_only
        self.provider = provider_override or (cloud_quota.provider_for_name(name) if exists else None)
        self._path = path
        self._exists = exists
        self._worker = None
        self.setFixedWidth(TILE_WIDTH)
        self.setObjectName("StorageTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        if provider_override:
            provider = "Google Drive" if provider_override == "google" else "Dropbox"
            account = display_account or ""
        else:
            provider, account = split_tile_name(name)

        top = QHBoxLayout()
        name_lbl = QLabel(provider)
        name_lbl.setObjectName("TileName")
        name_lbl.setToolTip(name)
        top.addWidget(name_lbl)
        top.addStretch()
        dot = "●" if exists else "○"
        status_lbl = QLabel(dot)
        status_lbl.setStyleSheet("color: #16a34a;" if exists else "color: #d1d5db;")
        top.addWidget(status_lbl)
        layout.addLayout(top)

        self.account_lbl = QLabel(account)
        self.account_lbl.setObjectName("TileAccount")
        self.account_lbl.setWordWrap(True)
        self.account_lbl.setToolTip(name)
        self.account_lbl.setVisible(bool(account))
        layout.addWidget(self.account_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        self.detail_lbl = QLabel()
        self.detail_lbl.setObjectName("TileFree")
        self.detail_lbl.setWordWrap(True)
        layout.addWidget(self.detail_lbl)

        if path is not None and exists:
            open_btn = link_button("Open in Finder →")
            open_btn.setStyleSheet(open_btn.styleSheet() + "font-size: 10px; padding: 2px 0;")
            open_btn.clicked.connect(lambda: run_cmd(["open", str(path)]))
            layout.addWidget(open_btn)

        if self.provider and exists and not cloud_quota.is_connected(self.account_key):
            connect_btn = link_button("Connect for account quota →")
            connect_btn.setStyleSheet(connect_btn.styleSheet() + "font-size: 10px; padding: 2px 0;")
            if on_connect_request:
                connect_btn.clicked.connect(lambda: on_connect_request(self.account_key, self.provider))
            layout.addWidget(connect_btn)

        self.reconnect_btn = link_button("Token expired — reconnect →")
        self.reconnect_btn.setStyleSheet(self.reconnect_btn.styleSheet() + "font-size: 10px; padding: 2px 0; color: #dc2626;")
        if on_connect_request:
            self.reconnect_btn.clicked.connect(lambda: self._do_reconnect(on_connect_request))
        self.reconnect_btn.setVisible(False)
        layout.addWidget(self.reconnect_btn)

        self.set_usage(path, exists)

    def _do_reconnect(self, on_connect_request):
        cloud_quota.disconnect(self.account_key)
        self.reconnect_btn.setVisible(False)
        self.detail_lbl.setText("Opening browser — sign in and approve access…")
        self._worker = ConnectWorker(self.provider, self.account_key)
        self._worker.done.connect(self._reconnect_done)
        self._worker.start()

    def _reconnect_done(self, ok, err):
        if ok:
            self.detail_lbl.setText("Reconnected!")
            self.set_usage(self._path, self._exists)
        else:
            self.detail_lbl.setText(f"Failed: {err}")
            self.reconnect_btn.setVisible(True)

    def _set_bar(self, pct_used):
        self.bar.setValue(pct_used)
        if pct_used >= 90:
            color = "#FF453A" if _DARK else "#FF3B30"
        elif pct_used >= 70:
            color = "#FF9F0A" if _DARK else "#FF9500"
        else:
            color = "#0A84FF" if _DARK else "#007AFF"
        bar_bg = "#48484A" if _DARK else "#E5E5EA"
        self.bar.setStyleSheet(
            f"QProgressBar {{ border:none; border-radius:4px; background:{bar_bg}; height:6px; }}"
            f"QProgressBar::chunk {{ border-radius:4px; background:{color}; }}"
        )

    def set_usage(self, path, exists):
        if not exists:
            self.bar.setValue(0)
            self.detail_lbl.setText("not mounted")
            return

        if self.provider and cloud_quota.is_connected(self.account_key):
            # Fetch Dropbox email dynamically (mount name doesn't include it)
            if self.provider == "dropbox":
                email = cloud_quota.dropbox_account_email(self.account_key)
                if email:
                    self.account_lbl.setText(email)
                    self.account_lbl.setVisible(True)
            try:
                result = cloud_quota.quota(self.account_key)
                quota_error = None
            except Exception as e:
                result = None
                quota_error = str(e)
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
            # Token likely expired or revoked
            expired = quota_error and ("400" in quota_error or "401" in quota_error)
            if expired:
                self.bar.setValue(0)
                self.detail_lbl.setText("")
                self.reconnect_btn.setVisible(True)
                return
            self.detail_lbl.setText(
                "Account quota unavailable" if self.quota_only
                else "Account quota unavailable — showing local disk:"
            )
            if self.quota_only:
                self.bar.setValue(0)
                return

        if self.quota_only:
            self.bar.setValue(0)
            self.detail_lbl.setText("Not connected yet")
            return

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
        add_btn = secondary_button("+ Add account")
        add_btn.clicked.connect(self.open_add_account_dialog)
        header.addWidget(add_btn)
        accounts_btn = secondary_button("☁ Cloud accounts…")
        accounts_btn.clicked.connect(self.open_accounts_dialog)
        header.addWidget(accounts_btn)
        self.vbox.addLayout(header)
        subtitle = QLabel(
            "Local disk free space for every mount, or real account quota once connected")
        subtitle.setObjectName("CardSubtitle")
        self.body(subtitle)

        self.tiles_row = QHBoxLayout()
        self.tiles_row.setSpacing(10)
        self.tiles_row.setContentsMargins(0, 0, 0, 0)
        self.body(self.tiles_row)
        self.tiles = []
        self.refresh()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5 * 60 * 1000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

    def refresh(self):
        for t in self.tiles:
            t.setParent(None)
        # Remove the trailing stretch added by the previous refresh
        while self.tiles_row.count():
            self.tiles_row.takeAt(0)
        self.tiles = []
        targets = [t for t in storage_targets() if t[2]]
        mounted_keys = {name for name, _path, _exists in targets}
        for name, path, exists in targets:
            tile = StorageTile(name, path, exists, on_connect_request=self.connect_account)
            self.tiles_row.addWidget(tile)
            self.tiles.append(tile)
        for acc in cloud_quota.load_manual_accounts():
            if acc["key"] in mounted_keys:
                continue
            tile = StorageTile(
                acc["key"], None, True,
                on_connect_request=self.connect_account,
                provider_override=acc["provider"], display_account=acc["label"],
                quota_only=True,
            )
            self.tiles_row.addWidget(tile)
            self.tiles.append(tile)
        self.tiles_row.addStretch()

    def open_accounts_dialog(self):
        CloudAccountsDialog(self, on_change=self.refresh).exec()

    def open_add_account_dialog(self):
        AddAccountDialog(self, on_change=self.refresh).exec()

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

    def _add_row(self, label_text, name, provider, removable=False):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
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
        if removable:
            rm_btn = secondary_button("Remove")
            rm_btn.clicked.connect(lambda _, n=name: self.do_remove(n))
            row.addWidget(rm_btn)
        w = QWidget()
        w.setLayout(row)
        self.rows_box.addWidget(w)

    def populate_rows(self):
        while self.rows_box.count():
            item = self.rows_box.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Deduplicate by base email (same logic as storage_targets)
        seen = {}
        for name, _path, exists in cloud_services():
            if not exists:
                continue
            p = cloud_quota.provider_for_name(name)
            if not p:
                continue
            _, account = split_tile_name(name)
            base = re.sub(r'\s+\(\d{2}-\d{2}-\d{4}.*\)$', '', account).strip()
            key = (p, base)
            if key not in seen or len(name) < len(seen[key][0]):
                seen[key] = (name, p)
        mounted = list(seen.values())
        manual = cloud_quota.load_manual_accounts()

        if not mounted and not manual:
            self.rows_box.addWidget(QLabel("No Google Drive / Dropbox mounts or added accounts found."))
            return

        if mounted:
            self.rows_box.addWidget(QLabel("Mounted folders:"))
            for name, provider in mounted:
                self._add_row(name, name, provider)

        if manual:
            self.rows_box.addWidget(QLabel("Added accounts:"))
            for acc in manual:
                self._add_row(acc["label"], acc["key"], acc["provider"], removable=True)

    def do_remove(self, account_key):
        cloud_quota.remove_manual_account(account_key)
        self.populate_rows()
        if self.on_change:
            self.on_change()

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


class AddAccountDialog(QDialog):
    """Add a Google Drive / Dropbox account to monitor, with no local mount required."""

    def __init__(self, parent=None, on_change=None):
        super().__init__(parent)
        self.on_change = on_change
        self.worker = None
        self.setWindowTitle("Add Account")
        self.resize(420, 220)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Monitor a Google Drive or Dropbox account's storage quota even if it\n"
            "isn't mounted locally. Needs the OAuth app credentials from\n"
            "Cloud Accounts… saved first."
        ))

        form = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Google Drive", "google")
        self.provider_combo.addItem("Dropbox", "dropbox")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. work.account@gmail.com")
        form.addRow("Provider:", self.provider_combo)
        form.addRow("Label:", self.label_edit)
        layout.addLayout(form)

        layout.addStretch()
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("CardSubtitle")
        layout.addWidget(self.status_lbl)

        row = QHBoxLayout()
        row.addStretch()
        cancel_btn = secondary_button("Cancel")
        cancel_btn.clicked.connect(self.reject)
        connect_btn = QPushButton("Connect…")
        connect_btn.clicked.connect(self.do_connect)
        row.addWidget(cancel_btn)
        row.addWidget(connect_btn)
        layout.addLayout(row)

    def do_connect(self):
        label = self.label_edit.text().strip()
        provider = self.provider_combo.currentData()
        if not label:
            self.status_lbl.setText("Enter a label for this account first.")
            return
        key = f"{provider}:{label}"
        existing = [a["key"] for a in cloud_quota.load_manual_accounts()]
        if key in existing or cloud_quota.is_connected(key):
            self.status_lbl.setText("An account with that label already exists.")
            return

        self.status_lbl.setText("Opening browser — sign in and approve access…")
        self.worker = ConnectWorker(provider, key)
        self.worker.done.connect(lambda ok, err: self._finished(ok, err, key, provider, label))
        self.worker.start()

    def _finished(self, ok, error, key, provider, label):
        if not ok:
            self.status_lbl.setText(f"Failed: {error}")
            return
        cloud_quota.add_manual_account(key, provider, label)
        if self.on_change:
            self.on_change()
        self.accept()


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
# Backup history dialog
# ----------------------------------------------------------------------------
class BackupHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backup History")
        self.resize(600, 360)
        layout = QVBoxLayout(self)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Date", "Started", "Duration", "Status"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

        runs = self._parse_runs()
        table.setRowCount(len(runs))
        for r, (date, started, duration, status) in enumerate(runs):
            for c, val in enumerate([date, started, duration, status]):
                item = QTableWidgetItem(val)
                if c == 3:
                    item.setForeground(
                        QColor("#16a34a") if val == "OK"
                        else QColor("#dc2626") if val == "ERRORS"
                        else QColor("#9ca3af")
                    )
                table.setItem(r, c, item)

        layout.addWidget(table)

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _parse_runs(self):
        logs = sorted(glob.glob(str(LOG_DIR / "backup_*.log")), reverse=True)[:15]
        runs = []
        for log_path in logs:
            text = Path(log_path).read_text(errors="replace")
            sm = re.search(
                r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\] ===== Backup run started", text)
            em = re.search(
                r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\] ===== Backup run finished", text)
            if not sm:
                continue
            date, started = sm.group(1), sm.group(2)
            duration = "—"
            if em:
                try:
                    t0 = datetime.strptime(f"{sm.group(1)} {sm.group(2)}", "%Y-%m-%d %H:%M:%S")
                    t1 = datetime.strptime(f"{em.group(1)} {em.group(2)}", "%Y-%m-%d %H:%M:%S")
                    secs = int((t1 - t0).total_seconds())
                    duration = f"{secs // 60}m {secs % 60}s"
                except ValueError:
                    pass
            status = "OK" if "finished OK" in text else "ERRORS" if "WITH ERRORS" in text else "—"
            runs.append((date, started, duration, status))
        return runs


# ----------------------------------------------------------------------------
# Backup status & schedule card
# ----------------------------------------------------------------------------
class BackupStatusCard(Card):
    def __init__(self):
        super().__init__("Google Drive Backup", "Status, schedule, and manual run")
        self.proc = None
        self._dry_run = False
        self._last_overdue_notify: datetime | None = None

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

        wake = QHBoxLayout()
        self.wake_lbl = QLabel()
        self.wake_btn = secondary_button("")
        self.wake_btn.clicked.connect(self.toggle_wake)
        wake.addWidget(self.wake_lbl)
        wake.addStretch()
        wake.addWidget(self.wake_btn)
        self.body(wake)

        login = QHBoxLayout()
        self.login_lbl = QLabel()
        self.login_btn = secondary_button("")
        self.login_btn.clicked.connect(self.toggle_login_item)
        login.addWidget(self.login_lbl)
        login.addStretch()
        login.addWidget(self.login_btn)
        self.body(login)

        runrow = QHBoxLayout()
        self.run_btn = QPushButton("▶  Run backup now")
        self.run_btn.clicked.connect(self.run_backup)
        self.dry_btn = secondary_button("⚟  Dry run")
        self.dry_btn.clicked.connect(self.run_dry_run)
        self.stop_btn = secondary_button("■  Stop")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setEnabled(False)
        self.history_btn = secondary_button("📋 History")
        self.history_btn.clicked.connect(lambda: BackupHistoryDialog(self).exec())
        runrow.addWidget(self.run_btn)
        runrow.addWidget(self.dry_btn)
        runrow.addWidget(self.stop_btn)
        runrow.addStretch()
        runrow.addWidget(self.history_btn)
        self.body(runrow)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        self.body(self.log)
        self._preload_log()

        self.refresh_schedule()
        self.refresh_wake()
        self.refresh_login_item()

        # Poll every 5 min so auto-backup fires shortly after 03:30 on wake.
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(5 * 60 * 1000)
        self._auto_timer.timeout.connect(self._maybe_auto_backup)
        self._auto_timer.start()
        # Also check immediately in case the app was just opened after a missed night.
        QTimer.singleShot(10_000, self._maybe_auto_backup)

        # Network-triggered backup: fire ~30 s after the Mac comes back online.
        if QNetworkInformation.load(QNetworkInformation.Feature.Reachability):
            net = QNetworkInformation.instance()
            net.reachabilityChanged.connect(self._on_reachability_changed)

    def _maybe_auto_backup(self):
        """Run the backup automatically if the schedule is on, it's past 03:30,
        and no backup has run since 03:30 today. Also notifies if >25 h overdue."""
        if self.proc is not None:
            return  # already running
        if not launchd_loaded():
            # Even if schedule is off, warn if backup is very overdue.
            age = last_backup_age_hours()
            if age is not None and age > 25:
                self._notify_overdue(
                    f"Last backup was {int(age)}h ago — schedule is disabled."
                )
            return

        now = datetime.now()
        if now.hour < 3 or (now.hour == 3 and now.minute < 30):
            # Before the backup window: warn if it's been >25 h since last successful run.
            age = last_backup_age_hours()
            if age is not None and age > 25:
                self._notify_overdue(f"Last successful backup was {int(age)}h ago.")
            return

        # Past 03:30 — check if a backup log exists for today with a timestamp >= 03:30.
        today_log = LOG_DIR / f"backup_{now.date()}.log"
        if today_log.exists():
            text = today_log.read_text(errors="replace")
            for m in re.finditer(
                r"\[(\d{4}-\d{2}-\d{2} (\d{2}):(\d{2}):\d{2})\] ===== Backup run started", text
            ):
                h, mi = int(m.group(2)), int(m.group(3))
                if h > 3 or (h == 3 and mi >= 30):
                    return  # already ran today after 03:30
        self.run_backup()

    def _notify_overdue(self, message: str) -> None:
        """Send an overdue-backup notification at most once per hour."""
        now = datetime.now()
        if self._last_overdue_notify and (now - self._last_overdue_notify).total_seconds() < 3600:
            return
        self._last_overdue_notify = now
        _notify("Backup Control Center", message, "Backup overdue")

    def _preload_log(self) -> None:
        """Show the tail of the most recent backup log at startup."""
        logs = sorted(glob.glob(str(LOG_DIR / "backup_*.log")))
        if not logs:
            return
        try:
            text = Path(logs[-1]).read_text(errors="replace")
        except OSError:
            return
        tail = "\n".join(text.splitlines()[-60:])
        self.log.setPlainText(tail)
        self.log.moveCursor(QTextCursor.End)

    def _on_reachability_changed(self, reachability):
        if reachability == QNetworkInformation.Reachability.Online:
            # Wait 30 s for Google Drive to mount before attempting backup.
            QTimer.singleShot(30_000, self._backup_on_network_up)

    def _backup_on_network_up(self):
        """Run backup when Mac comes online if no successful backup in the past 12 h."""
        if self.proc is not None:
            return
        if not launchd_loaded():
            return
        age = last_backup_age_hours()
        if age is None or age > 12:
            self.run_backup()

    def refresh_status(self):
        info, _ = last_backup_info()
        self.status_lbl.setText(info)

    def refresh_schedule(self):
        loaded = launchd_loaded()
        self.sched_lbl.setText(
            "🕒 Nightly schedule (03:30): " + ("ENABLED" if loaded else "disabled"))
        self.sched_btn.setText("Disable" if loaded else "Enable")

    def refresh_wake(self):
        active = wake_schedule_active()
        self.wake_lbl.setText(
            "⏰ Wake Mac at 03:25 for backup: " + ("ENABLED" if active else "disabled"))
        self.wake_btn.setText("Disable" if active else "Enable")

    def refresh_login_item(self):
        is_item = is_login_item()
        self.login_lbl.setText("🚀 Open at login: " + ("ENABLED" if is_item else "disabled"))
        self.login_btn.setText("Disable" if is_item else "Enable")

    def toggle_login_item(self):
        is_item = is_login_item()
        ok, err = set_login_item(not is_item)
        if not ok and err and "User cancelled" not in err:
            QMessageBox.warning(self, "Login Item", f"Could not change login item:\n{err}")
        self.refresh_login_item()

    def toggle_wake(self):
        if wake_schedule_active():
            ok, err = set_wake_schedule(False)
        else:
            ok, err = set_wake_schedule(True)
        if not ok:
            if err and "User cancelled" not in err:
                QMessageBox.warning(self, "Wake schedule", f"Could not update wake schedule:\n{err}")
        self.refresh_wake()

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
        self._dry_run = False
        self.log.clear()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_output)
        self.proc.finished.connect(self._finished)
        self.run_btn.setEnabled(False)
        self.dry_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.proc.start("/bin/bash", [str(SCRIPT)])

    def run_dry_run(self):
        if self.proc is not None:
            QMessageBox.information(self, "Busy",
                                    "Stop the running backup before starting a dry run.")
            return
        self._dry_run = True
        self.log.clear()
        self.log.insertPlainText("=== DRY RUN — no files will be changed ===\n\n")
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("DRY_RUN", "1")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_output)
        self.proc.finished.connect(self._finished)
        self.run_btn.setEnabled(False)
        self.dry_btn.setEnabled(False)
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
        was_dry = self._dry_run
        self._dry_run = False
        self.run_btn.setEnabled(True)
        self.dry_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.proc = None
        self.refresh_status()
        if not was_dry:
            info, _ = last_backup_info()
            if "OK" in info:
                _notify("Backup Control Center", "Backup completed successfully.", "Google Drive Backup")
            elif "ERRORS" in info:
                _notify("Backup Control Center", "Backup finished with errors — check the log.", "Google Drive Backup")


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
        folder_name = item.text()
        answer = QMessageBox.question(
            self, "Remove folder",
            f'Remove “{folder_name}” from the backup?\n\nFiles already in Google Drive are not deleted.',
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        folders = [f for f in read_folders() if f != item.text()]
        write_folders(folders)
        self.reload_folders()

    def edit_excludes(self):
        ExcludesDialog(self).exec()


class LabHealthCard(Card):
    def __init__(self):
        super().__init__("Lab Health", "Disk usage, git status, and reclaimable space per active project")
        self.summary_lbl = QLabel("Scanning…")
        self.summary_lbl.setObjectName("CardSubtitle")
        self.body(self.summary_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["", "Project", "Total", "Reclaimable", "Git", "Manifest / .env"])
        header = self.table.horizontalHeader()
        for col in range(5):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(280)
        self.body(self.table)

        row = QHBoxLayout()
        rescan = secondary_button("🔄 Rescan")
        rescan.clicked.connect(self.rescan)
        clean = secondary_button("🧹 Clean up checked")
        clean.clicked.connect(self.clean_checked)
        row.addWidget(rescan)
        row.addWidget(clean)
        row.addStretch()
        self.body(row)

        hint = QLabel(
            "Reclaimable = .venv, build, dist, __pycache__ and similar — git-ignored, "
            "excluded from the Drive backup, and rebuildable with uv sync / pip install.")
        hint.setObjectName("CardSubtitle")
        hint.setWordWrap(True)
        self.body(hint)

        self._rows = []
        self.rescan()

    def rescan(self):
        self.summary_lbl.setText("Scanning…")
        self.worker = LabHealthWorker()
        self.worker.done.connect(self._populate)
        self.worker.start()

    def _populate(self, rows):
        self._rows = rows
        self.table.setRowCount(len(rows))
        total_reclaim_kb = 0

        for r, row in enumerate(rows):
            chk = QTableWidgetItem()
            if row["reclaim_kb"] > 0:
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Checked)
            else:
                chk.setFlags(Qt.NoItemFlags)
            self.table.setItem(r, 0, chk)

            self.table.setItem(r, 1, QTableWidgetItem(row["name"]))
            self.table.setItem(r, 2, QTableWidgetItem(human_size(row["total_kb"] * 1024)))
            self.table.setItem(
                r, 3, QTableWidgetItem(
                    human_size(row["reclaim_kb"] * 1024) if row["reclaim_kb"] else "—"))
            total_reclaim_kb += row["reclaim_kb"]

            if not row["has_git"]:
                git_text, git_color = "no git repo", "#dc2626"
            elif row["uncommitted"]:
                git_text, git_color = f"{row['uncommitted']} uncommitted", "#d97706"
            else:
                git_text, git_color = f"clean ({row['last_commit']})", "#16a34a"
            git_item = QTableWidgetItem(git_text)
            git_item.setForeground(QColor(git_color))
            self.table.setItem(r, 4, git_item)

            notes = [] if row["has_manifest"] else ["⚠️ no requirements.txt / pyproject.toml"]
            if row["env_flag"]:
                notes.append(row["env_flag"])
            notes_item = QTableWidgetItem("; ".join(notes) if notes else "—")
            if notes:
                notes_item.setForeground(QColor("#d97706"))
            self.table.setItem(r, 5, notes_item)

        n_reclaim = sum(1 for row in rows if row["reclaim_kb"] > 0)
        self.summary_lbl.setText(
            f"{human_size(total_reclaim_kb * 1024)} reclaimable across {n_reclaim} of "
            f"{len(rows)} projects"
        )

    def clean_checked(self):
        targets = []  # (project_name, path, kb)
        for r, row in enumerate(self._rows):
            item = self.table.item(r, 0)
            if item and item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                for p, kb in row["reclaim_items"]:
                    targets.append((row["name"], p, kb))

        if not targets:
            QMessageBox.information(
                self, "Nothing to clean", "No checked projects have reclaimable space.")
            return

        total_kb = sum(kb for _, _, kb in targets)
        listing = "\n".join(f"  {name}/{p.name}  ({human_size(kb * 1024)})"
                             for name, p, kb in targets[:20])
        if len(targets) > 20:
            listing += f"\n  … and {len(targets) - 20} more"
        answer = QMessageBox.question(
            self, "Clean up disposable folders",
            f"Delete these {len(targets)} folders, reclaiming "
            f"{human_size(total_kb * 1024)}?\n\n{listing}\n\n"
            "These are git-ignored and excluded from the Drive backup — rebuild with "
            "uv sync / pip install -r requirements.txt when you next need them.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return

        errors = []
        for name, p, _ in targets:
            try:
                shutil.rmtree(p)
            except Exception as e:
                errors.append(f"{name}/{p.name}: {e}")
        if errors:
            QMessageBox.warning(self, "Some deletions failed", "\n".join(errors))
        self.rescan()


# ----------------------------------------------------------------------------
# In-app documentation viewer
# ----------------------------------------------------------------------------
class DocViewerDialog(QDialog):
    def __init__(self, parent, title, path):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 720)
        layout = QVBoxLayout(self)

        viewer = QTextBrowser()
        viewer.setOpenExternalLinks(True)
        path = Path(path)
        if path.exists():
            viewer.setMarkdown(path.read_text(errors="replace"))
        else:
            viewer.setPlainText(f"File not found:\n{path}")
        layout.addWidget(viewer)

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        layout.addLayout(row)


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
            ("App guide (README)", lambda _=False, t="App Guide", p=app_dir / "README.md": self.open_doc(t, p)),
            ("Backup strategy", lambda _=False, t="Backup Strategy", p=BACKUP_DIR / "BACKUP_STRATEGY.md": self.open_doc(t, p)),
            ("Google Drive setup", lambda _=False, t="Google Drive Setup", p=BACKUP_DIR / "SETUP.md": self.open_doc(t, p)),
            ("Proton vault guide", lambda _=False, t="Proton Vault Guide", p=BACKUP_DIR / "PROTON_VAULT.md": self.open_doc(t, p)),
            ("Lab overview", lambda _=False, t="Lab Overview", p=DOCS / "lab" / "README.md": self.open_doc(t, p)),
        ]
        accounts = [
            ("Google One storage", "https://one.google.com/storage"),
            ("Dropbox plan & usage", "https://www.dropbox.com/account/plan"),
            ("Proton storage dashboard", "https://account.proton.me/u/0/drive"),
            ("iCloud storage settings",
             lambda: run_cmd(["open", "x-apple.systempreferences:com.apple.systempreferences.AppleIDSettings"])),
        ]

        extras = [
            ("Google Photos Takeout…", self._google_photos_help),
            ("Proton vault status", self._proton_vault_check),
            ("Time Machine: back up now",
             lambda: run_cmd(["tmutil", "startbackup"])),
        ]

        grid.addLayout(col("Open locations", locations), 0, 0)
        grid.addLayout(col("Documentation", docs), 0, 1)
        grid.addLayout(col("Account pages", accounts), 0, 2)
        grid.addLayout(col("Tools", extras), 1, 0)
        self.body(grid)

    def open_doc(self, title, path):
        DocViewerDialog(self, title, path).exec()

    def _google_photos_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Google Photos Takeout → Mac")
        msg.setText(
            "How to download your Google Photos library to this Mac:\n\n"
            "1.  Open takeout.google.com → Deselect all → tick Google Photos only.\n"
            "2.  Choose file type (.zip), frequency (once), and max size (2 GB).\n"
            "3.  Download the ZIP(s) when the email arrives.\n"
            "4.  Open the Photos app → File → Import → select the extracted folders.\n"
            "5.  After import, run Time Machine to include the Photos library in your\n"
            "    local backup.\n\n"
            "Tip: use 'google-photos-takeout-helper' (pip install) to merge multiple\n"
            "Takeout ZIPs into a single date-organised folder before importing."
        )
        msg.addButton("Open takeout.google.com", QMessageBox.ActionRole).clicked.connect(
            lambda: run_cmd(["open", "https://takeout.google.com"]))
        msg.addButton("Close", QMessageBox.RejectRole)
        msg.exec()

    def _proton_vault_check(self):
        vault_candidates = list(CLOUD_DIR.glob("ProtonDrive-*")) if CLOUD_DIR.exists() else []
        if not vault_candidates:
            QMessageBox.warning(self, "Proton Drive",
                                "No Proton Drive folder found in ~/Library/CloudStorage.\n"
                                "Is the Proton Drive desktop app running?")
            return
        issues = []
        for vault_path in vault_candidates:
            try:
                entries = list(vault_path.iterdir())
                if not entries:
                    issues.append(f"{vault_path.name}: folder is empty (not synced?).")
            except PermissionError:
                issues.append(f"{vault_path.name}: permission denied — check Full Disk Access.")
            except OSError as e:
                issues.append(f"{vault_path.name}: {e}")
        if issues:
            QMessageBox.warning(self, "Proton Drive", "\n".join(issues))
        else:
            names = ", ".join(p.name for p in vault_candidates)
            QMessageBox.information(self, "Proton Drive",
                                    f"Proton Drive appears accessible:\n{names}")


# ----------------------------------------------------------------------------
# Scroll area that yields wheel events to inner scrollable children
# so scrolling a log box / folder list doesn't scroll the whole window.
# ----------------------------------------------------------------------------
class SmartScrollArea(QScrollArea):
    _SCROLLABLES = (QTextEdit, QPlainTextEdit, QListWidget, QTableWidget)

    def wheelEvent(self, event):
        # Find the widget under the cursor
        w = QApplication.widgetAt(event.globalPosition().toPoint())
        while w is not None:
            if isinstance(w, self._SCROLLABLES):
                QApplication.sendEvent(w, event)
                return
            if w is self:
                break
            w = w.parent()
        super().wheelEvent(event)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Control Center")
        self.resize(1000, 880)
        self.setMinimumWidth(900)

        scroll = SmartScrollArea()
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
        self.health_card = LabHealthCard()
        self.tools_card = ToolsCard()

        outer.addWidget(self.storage_card)
        outer.addWidget(self.backup_card)
        outer.addWidget(self.folders_card)
        outer.addWidget(self.health_card)
        outer.addWidget(self.tools_card)
        outer.addStretch()

        scroll.setWidget(content)
        self.setCentralWidget(scroll)

        # Tray icon — patch backup_card._finished to keep tray in sync.
        self.tray = BackupTrayIcon(self)
        original_finished = self.backup_card._finished

        def _patched_finished():
            original_finished()
            self.tray.update_status()

        self.backup_card._finished = _patched_finished

    def refresh_all(self):
        self.storage_card.refresh()
        self.backup_card.refresh_status()
        self.backup_card.refresh_schedule()
        self.folders_card.reload_folders()
        self.health_card.rescan()
        self.tray.update_status()


# ----------------------------------------------------------------------------
# Menu-bar / system-tray companion
# ----------------------------------------------------------------------------
class BackupTrayIcon(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__()
        self._window = window

        # Use the app's icon asset if available, fall back to a built-in stock icon.
        icon_path = Path(__file__).resolve().parent / "assets" / "icon.icns"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            self.setIcon(QIcon.fromTheme("document-save",
                         QApplication.style().standardIcon(
                             QApplication.style().StandardPixmap.SP_DriveHDIcon)))

        menu = QMenu()
        self._status_action = menu.addAction("Checking…")
        self._status_action.setEnabled(False)
        menu.addSeparator()
        show_action = menu.addAction("Show Backup Control Center")
        show_action.triggered.connect(self._show_window)
        run_action = menu.addAction("Run Backup Now")
        run_action.triggered.connect(lambda: (self._show_window(),
                                              window.backup_card.run_backup()))
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self.setContextMenu(menu)

        self.activated.connect(self._activated)
        self.update_status()
        self.show()

    def update_status(self, info: str | None = None):
        if info is None:
            info, _ = last_backup_info()
        short = info.replace("Last run: ", "").replace("No backups run yet.", "Never backed up")
        self.setToolTip(f"Backup Control Center\n{short}")
        self._status_action.setText(short)

    def _show_window(self):
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()


_INSTANCE_LOCK_FILE = cloud_quota.SECRETS_DIR / "gui.lock"
_instance_lock_fd = None  # kept open so the OS holds the lock for our lifetime


def _acquire_instance_lock():
    """Grab an exclusive flock on a lock file. Returns True for the first instance."""
    global _instance_lock_fd
    cloud_quota.SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = open(_INSTANCE_LOCK_FILE, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        _instance_lock_fd = fd  # keep fd alive so the lock holds
        return True
    except BlockingIOError:
        return False


def main():
    if not _acquire_instance_lock():
        # Show a native alert, then bring the existing window to front.
        subprocess.run(
            ["osascript", "-e",
             'display alert "Backup Control Center is already open." '
             'message "Only one instance can run at a time." '
             'buttons {"OK"} default button "OK" '
             'giving up after 8\n'
             'tell application "Backup Control Center" to activate'],
            check=False,
        )
        sys.exit(0)

    global _DARK
    _DARK = _system_dark_mode()
    app = QApplication(sys.argv)
    app.setStyleSheet(build_app_style(_DARK))
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
