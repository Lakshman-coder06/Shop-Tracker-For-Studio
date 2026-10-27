"""
database.py   (APP SIDE - network version)
-------------------------------------------
This file REPLACES the old database.py that opened a private SQLite file
on each PC. That old design is exactly why Worker 1's jobs never showed up
on the Admin's computer: every PC had its own separate database.

Now there is ONE shared database, living on the shop server
(see the ShopTrackerServer folder). This module keeps every function name
the screens already use - get_transactions(), create_transaction(),
record_payment(), ... - but each one simply asks the server to do the work
and hands back the answer. So no screen had to be rewritten.

What you get back is the same shape as before: rows are dictionaries, so
row["amount"], row["worker_name"] etc. work exactly as they did.

Errors are explicit, never silent. If the server can't be reached while
you are saving something, an exception is raised and the screen shows a
clear message - a sale is never quietly thrown away.
"""

import threading
import time
from datetime import datetime

import requests

API_VERSION = 1
CONNECT_TIMEOUT = 3.0     # seconds to wait for the server to answer at all
READ_TIMEOUT = 15.0       # seconds to wait for a reply once connected
COOLDOWN_SECONDS = 4.0    # after a failure, fail instantly for a few seconds
                          # instead of freezing the screen on every refresh


# ---------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------

class DuplicateNameError(Exception):
    """A service (or other uniquely-named record) already exists."""


class LastAdminError(Exception):
    """Refused: this would deactivate the only remaining active Admin."""


class ShopServerError(Exception):
    """Base class for everything that can go wrong talking to the server."""


class ServerUnavailableError(ShopServerError):
    """The server could not be reached. Nothing was changed."""


class ServerTimeoutError(ServerUnavailableError):
    """The request was sent but no answer came back in time. If this was a
    SAVE, it may or may not have gone through - check before saving again."""


class AuthExpiredError(ShopServerError):
    """The login is no longer valid (expired, or the account was disabled)."""


class PermissionDeniedError(ShopServerError):
    """The server refused: this account is not allowed to do that."""


class LoginLockedError(ShopServerError):
    """Too many wrong PINs - login is temporarily blocked."""


class RemoteError(ShopServerError):
    """The server understood the request but could not complete it."""


# ---------------------------------------------------------------------
# Connection state
# ---------------------------------------------------------------------

_session = requests.Session()
_session_lock = threading.RLock()
_base_url = ""
_token = None
_down_until = 0.0


def configure(server_url: str):
    """Point this app at the shop server, e.g. 'http://192.168.1.20:8000'."""
    global _base_url, _token, _down_until
    with _session_lock:
        _base_url = (server_url or "").strip().rstrip("/")
        _token = None
        _down_until = 0.0


def get_server_url() -> str:
    return _base_url


def logout():
    """Forget the login token (called when returning to the login screen)."""
    global _token
    _token = None


def init_db():
    """Kept so old code calling it still works. The real database now lives
    on the server and is created there."""
    return None


# ---------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------

def _encode(obj):
    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}
    if isinstance(obj, (list, tuple)):
        return [_encode(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    return obj


def _decode(obj):
    if isinstance(obj, dict):
        if set(obj.keys()) == {"__datetime__"}:
            return datetime.fromisoformat(obj["__datetime__"])
        return {k: _decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode(v) for v in obj]
    return obj


def _detail(resp, default):
    try:
        d = resp.json().get("detail")
        if isinstance(d, str) and d:
            return d
    except Exception:
        pass
    return default


def _post(path, payload, auth=True, is_write=False):
    """One request to the server, with all the failure cases turned into
    clear exceptions."""
    global _down_until
    if not _base_url:
        raise ServerUnavailableError("No server address is set. Use 'Change server' on the login screen.")
    if time.monotonic() < _down_until:
        raise ServerUnavailableError(
            f"Can't reach the shop server at {_base_url}. Check that the server PC is on and this PC is on the same network."
        )

    headers = {}
    if auth and _token:
        headers["Authorization"] = "Bearer " + _token

    try:
        with _session_lock:
            resp = _session.post(_base_url + path, json=payload, headers=headers,
                                 timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except requests.exceptions.ReadTimeout:
        _down_until = time.monotonic() + COOLDOWN_SECONDS
        raise ServerTimeoutError(
            "The server did not answer in time."
            + (" If you were saving something, check the list first - it may have been saved." if is_write else "")
        )
    except requests.exceptions.SSLError:
        raise ServerUnavailableError(
            f"A secure (https) connection to {_base_url} failed. If the server doesn't use https, "
            f"change the address to start with http://"
        )
    except requests.exceptions.RequestException:
        _down_until = time.monotonic() + COOLDOWN_SECONDS
        raise ServerUnavailableError(
            f"Can't reach the shop server at {_base_url}. Check that the server PC is on and this PC is on the same network."
        )

    _down_until = 0.0
    code = resp.status_code
    if code in (502, 503, 504):
        _down_until = time.monotonic() + COOLDOWN_SECONDS
        raise ServerUnavailableError("The shop server is starting up or temporarily unavailable. Try again in a moment.")
    if code == 401:
        raise AuthExpiredError(_detail(resp, "Your login has expired. Please log in again."))
    if code == 403:
        raise PermissionDeniedError(_detail(resp, "You do not have permission to do that."))
    if code == 429:
        raise LoginLockedError(_detail(resp, "Too many attempts. Please wait a few minutes."))
    if code == 404:
        raise RemoteError("The server does not recognise this action. The app and the server may be different versions.")
    if code >= 400:
        raise RemoteError(_detail(resp, f"The server could not complete that (error {code})."))
    try:
        return resp.json()
    except ValueError:
        raise RemoteError("The server sent an unreadable reply. Is the address pointing at the right server?")


_WRITE_PREFIXES = ("create_", "record_", "mark_", "cancel_", "save_", "update_", "set_", "admin_",
                   "change_", "add_", "assign_", "start_", "end_", "log_")


def _call(fn, args, kwargs):
    reply = _post("/api/rpc", {"fn": fn, "args": _encode(args), "kwargs": _encode(kwargs)},
                  is_write=fn.startswith(_WRITE_PREFIXES))
    if reply.get("ok"):
        return _decode(reply.get("result"))
    err = reply.get("error") or {}
    kind, msg = err.get("type"), err.get("message") or "The server could not complete that."
    if kind == "DuplicateNameError":
        raise DuplicateNameError(msg)
    if kind == "LastAdminError":
        raise LastAdminError(msg)
    if kind == "ValueError":
        raise ValueError(msg)
    raise RemoteError(msg)


# ---------------------------------------------------------------------
# Login / connection checks
# ---------------------------------------------------------------------

def authenticate(name: str, pin: str):
    """Name + PIN login. Returns the user (a dict) on success, or None if
    the name or PIN is wrong - same answer either way, so a mistyped name
    never reveals whether it exists. Raises LoginLockedError if too many
    wrong attempts were made, or ServerUnavailableError if the server
    can't be reached."""
    global _token
    try:
        reply = _post("/api/login", {"name": name, "pin": pin}, auth=False)
    except AuthExpiredError:   # the server's 401 on /login means "wrong name or PIN"
        return None
    _token = reply["token"]
    return _decode(reply["user"])


def check_server(url: str = None, timeout: float = 4.0) -> dict:
    """Used by 'Test connection'. Never raises. Returns
    {'ok': bool, 'message': str}."""
    target = (url if url is not None else _base_url).strip().rstrip("/")
    if not target:
        return {"ok": False, "message": "Enter the server address first."}
    try:
        r = requests.get(target + "/api/health", timeout=timeout)
    except requests.exceptions.SSLError:
        return {"ok": False, "message": "Secure connection failed. If your server does not use https, "
                                         "start the address with http://"}
    except requests.exceptions.RequestException:
        return {"ok": False, "message": "Could not reach that address. Check the server PC is on, the "
                                         "address is right, and this PC is on the same network."}
    try:
        info = r.json()
    except ValueError:
        return {"ok": False, "message": "Something answered, but it is not a Thalapathi Studio server."}
    if info.get("app") != "Thalapathi Studio":
        return {"ok": False, "message": "Something answered, but it is not a Thalapathi Studio server."}
    if info.get("api_version") != API_VERSION:
        return {"ok": False, "message": "The server and this app are different versions. Update them both to the same release."}
    return {"ok": True, "message": f"Connected to the Thalapathi Studio server (v{info.get('server_version', '?')})."}


def ping() -> bool:
    """Fast yes/no for the little connection light in the header."""
    if not _base_url or time.monotonic() < _down_until:
        return False
    try:
        r = requests.get(_base_url + "/api/health", timeout=(2.0, 3.0))
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


# ---------------------------------------------------------------------
# Every database function the screens use. Each one is forwarded to the
# server, which checks permissions and runs the real database code.
# ---------------------------------------------------------------------

_RPC_FUNCTIONS = [
    'get_active_workers', 'get_active_services', 'get_user_by_id', 'change_own_pin',
    'check_db_connection', 'get_last_activity_saved', 'get_today_summary',
    'get_worker_performance_today', 'get_today_transaction_totals', 'get_todo_dashboard_counts',
    'start_worker_session', 'end_worker_session', 'log_activity_start', 'log_activity_end',
    'get_recent_activity', 'get_activity_history', 'get_activity_by_id', 'get_distinct_activity_apps',
    'get_today_app_usage_totals', 'get_possible_missed_entries', 'create_transaction',
    'get_transactions', 'get_pending_transactions', 'get_transaction_payments', 'record_payment',
    'mark_transaction_completed', 'mark_transaction_in_progress', 'cancel_transaction',
    'create_expense', 'get_expenses_today', 'get_daily_totals_for_closing', 'get_daily_closing',
    'save_daily_closing', 'get_all_workers_admin', 'create_worker', 'update_worker',
    'set_worker_status', 'admin_reset_pin', 'get_all_services_admin', 'create_service',
    'update_service_rate', 'set_service_active', 'get_audit_logs', 'create_enquiry', 'get_enquiries',
    'get_enquiry_comments', 'add_enquiry_comment', 'update_enquiry_status', 'assign_enquiry',
    'create_todo', 'get_todos', 'update_todo_status',
]


def _make_remote_function(name):
    def remote(*args, **kwargs):
        return _call(name, args, kwargs)
    remote.__name__ = name
    remote.__qualname__ = name
    remote.__doc__ = f"Runs {name}() on the shop server."
    return remote


for _name in _RPC_FUNCTIONS:
    globals()[_name] = _make_remote_function(_name)
del _name
