"""
paths.py
---------
Resolves where Thalapathi Studio's writable files (the SQLite database
and the theme/settings file) should live, and provides a safe one-time
migration from the old "next to the app" location to a proper per-user
writable folder.

WHY THIS EXISTS: before this change, database.py and app_settings.py
each computed their file's path as "the folder this .py file lives in."
That works fine for `python main.py` during development, but breaks for
a real Windows install: once the app is installed to somewhere like
C:\\Program Files\\Thalapathi Studio\\, that folder is NOT writable by a
normal user account, so the app could never create or update its own
database or settings file there - it needs a proper per-user writable
location instead, which on Windows is %LOCALAPPDATA%.

Both database.py and app_settings.py now call migrate_file_if_needed()
for their one file, so this logic (and its safety rules) lives in
exactly one place instead of being duplicated.
"""

import os
import sys
import shutil

APP_FOLDER_NAME = "Thalapathi Studio"


def get_app_data_dir() -> str:
    """
    The persistent, per-user, always-writable folder for this app's data:
        %LOCALAPPDATA%\\Thalapathi Studio\\   on Windows

    Created automatically if it doesn't exist yet. On non-Windows
    platforms (only ever relevant for development/testing - this app
    targets Windows) falls back to a sensible per-user folder instead,
    so nothing here ever crashes for lack of a LOCALAPPDATA variable.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            # Extremely unlikely on real Windows, but never crash over it.
            base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")

    app_dir = os.path.join(base, APP_FOLDER_NAME)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def get_legacy_app_dir() -> str:
    """
    Where this app's files used to live: right next to the running
    application - the folder containing main.py during development, or
    the folder containing the .exe once built with PyInstaller. This is
    ONLY ever read from (to find something to migrate) - never written
    to, since that folder may not be writable at all once installed.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def migrate_file_if_needed(filename: str) -> str:
    """
    Returns the correct, current path for `filename` inside the app-data
    directory - and gets it there safely first, if needed:

      - If `filename` already exists in the new app-data folder, that
        path is returned immediately. Nothing is ever overwritten here.
      - Otherwise, if an older copy exists next to the application (from
        before this change, or from development), it is COPIED (not
        moved) into the new location - the original is left exactly
        where it was, so nothing is ever deleted or destroyed by this.
      - If neither exists, the new (empty) path is returned as-is, and
        the caller creates a fresh file there as normal.
    """
    new_dir = get_app_data_dir()
    new_path = os.path.join(new_dir, filename)
    if os.path.exists(new_path):
        return new_path

    legacy_path = os.path.join(get_legacy_app_dir(), filename)
    if os.path.exists(legacy_path) and os.path.isfile(legacy_path):
        try:
            shutil.copy2(legacy_path, new_path)
        except Exception:
            # A failed copy should never stop the app from starting - it
            # just starts fresh at new_path, same as a first-ever run.
            pass

    return new_path
