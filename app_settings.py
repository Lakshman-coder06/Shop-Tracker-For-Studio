"""
app_settings.py
-----------------
A tiny local settings file for app-level display preferences - right
now, just the theme (Light / Dark / System). Deliberately kept OUT of
the SQLite database: this is a UI preference, not shop data, and a
separate plain file means this feature can never touch, migrate, or put
at risk any business record (workers, jobs, transactions, payments,
etc.). Nothing here is created, read, or written by database.py.
"""

import json
import os
import re
from urllib.parse import urlparse

import paths

SETTINGS_FILE = paths.migrate_file_if_needed("app_settings.json")

VALID_THEMES = {"light", "dark", "system"}
DEFAULT_SETTINGS = {"theme": "system", "server_url": ""}  # System (Default) theme on first run; no server yet


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        if isinstance(data, dict):
            merged.update(data)
        return merged
    except Exception:
        # A corrupted/unreadable settings file should never stop the app
        # from starting - fall back to defaults.
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> bool:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f)
        return True
    except Exception:
        return False


def get_theme() -> str:
    """Returns the SAVED theme preference: 'light', 'dark', or 'system'."""
    theme = load_settings().get("theme", "system")
    return theme if theme in VALID_THEMES else "system"


def set_theme(theme: str) -> bool:
    if theme not in VALID_THEMES:
        return False
    settings = load_settings()
    settings["theme"] = theme
    return save_settings(settings)


def detect_system_scheme() -> str:
    """Asks Qt what the OS's current light/dark preference is. Returns
    'light' or 'dark' - never 'system' - with 'light' as the safe
    fallback if detection isn't available on this machine/Qt version."""
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
        return "light"
    except Exception:
        return "light"


def resolve_theme(theme: str = None) -> str:
    """Turns a saved setting ('light' / 'dark' / 'system') into an actual
    'light' or 'dark' to render. Pass nothing to resolve the currently
    saved preference."""
    if theme is None:
        theme = get_theme()
    if theme == "system":
        return detect_system_scheme()
    if theme == "dark":
        return "dark"
    return "light"


# ---------------------------------------------------------------------
# Shop server address (this PC only - NOT shop data)
# ---------------------------------------------------------------------

def normalize_server_url(text: str) -> str:
    """Tidies whatever a person types into a usable server address.
        '192.168.1.20'            -> 'http://192.168.1.20:8000'
        '192.168.1.20:9000'       -> 'http://192.168.1.20:9000'
        'myshop.onrender.com'     -> 'https://myshop.onrender.com'
        'http://shop-pc:8000/'    -> 'http://shop-pc:8000'
    Returns '' for empty input."""
    t = (text or "").strip().strip("/")
    if not t:
        return ""
    if "://" not in t:
        host_port = t.split("/")[0]
        host = host_port.split(":")[0]
        has_port = ":" in host_port
        is_ip = re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) is not None
        local_name = host.lower() == "localhost" or "." not in host or host.lower().endswith(".local")
        if is_ip or local_name or has_port:
            t = "http://" + t
        else:
            t = "https://" + t   # a normal web address, e.g. a cloud host
    parsed = urlparse(t)
    host = parsed.hostname or ""
    is_ip = re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) is not None
    local_name = host.lower() == "localhost" or "." not in host or host.lower().endswith(".local")
    if parsed.scheme == "http" and parsed.port is None and (is_ip or local_name):
        t = t.rstrip("/") + ":8000"   # the server's default port
    return t.rstrip("/")


def get_server_url() -> str:
    return load_settings().get("server_url", "") or ""


def set_server_url(url: str) -> bool:
    settings = load_settings()
    settings["server_url"] = normalize_server_url(url)
    return save_settings(settings)
