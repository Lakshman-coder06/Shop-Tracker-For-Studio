> **v11 - SHARED SHOP VERSION.** This app no longer stores data on each PC. It connects to
> one shared shop server (see `START_HERE.md` in the folder above). Anything below that
> mentions a per-PC `shop_tracker.db` or `%LOCALAPPDATA%` database describes the OLD
> single-PC design; the screens and business rules it describes are otherwise unchanged.

# Thalapathi Studio 💻 (formerly ShopTracker) — Correction Pass

> **Latest patch (this version):** the database and settings file now
> live in `%LOCALAPPDATA%\Thalapathi Studio\` instead of next to the
> application - required for a real Windows install (e.g.
> `C:\Program Files\Thalapathi Studio\`), which a normal user account
> cannot write to. A safe first-run migration copies any existing data
> from the old location automatically. See "Production install: database
> and settings location" below for full details and test results.

> **Latest patch (this version):** two small, scoped additions on top of
> everything below — a **Light / Dark / System (Default)** theme setting
> in Settings, and confirmation that the app name is "Thalapathi Studio
> 💻" everywhere. Nothing else was touched: no layout, sidebar, dashboard,
> feature, or database changes. See "Theme setting" section below for
> details and test results.

## Theme setting (Light / Dark / System)

New: `app_settings.py` (a tiny local JSON file, `app_settings.json`,
created next to `shop_tracker.db` - **not inside the SQLite database at
all**, precisely so this feature can never touch business data).
`theme.py` was restructured into one shared QSS template with two colour
sets (Light, Dark) filled in - the Light values are byte-for-byte the
same as before this patch, so "Light" is exactly the existing
appearance. Dark uses the same structure with a dark, readable palette
and the same green/teal accent for brand consistency.

Settings now has an "Appearance" dropdown between Account Details and
Change PIN. Choosing Light or Dark applies immediately and is saved;
choosing System (Default) - what a brand-new install starts with -
follows the OS's current light/dark preference via
`QGuiApplication.styleHints().colorScheme()`, falling back to Light if
that can't be detected.

A handful of colours that live outside the global stylesheet (the login
screen's background/card/text, and the header's two text labels) were
updated to read from the same palette, since those would otherwise stay
frozen in light colours and become unreadable in Dark mode - this is the
minimum needed for "proper dark background, readable text" to actually
be true, not a design change. Every other inline colour (status
messages like "Cash matches" / errors, sidebar icons, etc.) is
unchanged and stays the same colour in both themes, matching how most
apps treat semantic status colours.

**Tests performed** (all 10 items from your list, against the shipped
files):
1. Application opens successfully.
2. Confirmed "Thalapathi Studio" in both the login window's title bar
   and its on-screen branding label.
3. Confirmed Settings' dropdown contains exactly Light, Dark, System
   (Default).
4. Confirmed a fresh install's saved setting is `system`, and that it
   resolves to a real theme without crashing.
5. Switched to Light, confirmed the app stylesheet updated and the
   choice was saved.
6. Switched to Dark, confirmed the app stylesheet updated, saved
   correctly, **and** confirmed the header's two labels re-coloured
   live (no restart needed) - rendered actual PNG screenshots of the
   login screen, dashboard, and Settings in Dark mode to visually
   confirm readability rather than just trusting the stylesheet.
7. Confirmed the choice survives an actual fresh process restart (not
   just re-reading the setting in the same process - Qt only allows one
   `QApplication` per process, so I launched a second real Python
   process to confirm this properly).
8. Clicked through every sidebar page for both Worker (10 pages) and
   Admin (13 pages) after switching themes repeatedly - no crashes.
9. Logged in with name+PIN as both a worker and Admin - unchanged and
   working.
10. Re-ran job creation (including the fixed-rate lock), Worker-to-Worker
    data privacy, and Admin's cross-worker visibility - all unchanged
    and working.

**Database safety confirmed:** compared the full table list before and
after this patch - still exactly the same 12 business tables (users,
services, transactions, payments, expenses, enquiries, todos,
worker_sessions, application_activity, daily_closing, audit_logs,
enquiry_comments) plus SQLite's own `sqlite_sequence`. Nothing was
added, removed, or altered. `database.py` itself has zero new
`CREATE TABLE` or `ALTER TABLE` statements from this patch.

A real bug did surface during testing (and was fixed before shipping):
`main.py` tried to apply the saved theme before `self.dashboard` was
initialized, causing an `AttributeError` on startup - caught by actually
running the app, not by reading the code.

## Production install: database and settings location

New: `paths.py` - one small shared module that both `database.py` and
`app_settings.py` now use to find their file.

**The problem this fixes:** both files previously computed their path as
"the folder this .py file lives in." That's fine for `python main.py`
during development, but a real Windows install under something like
`C:\Program Files\Thalapathi Studio\` is not writable by a normal user
account - the app could never create or update its own database or
settings there.

**The fix:** both now resolve to `%LOCALAPPDATA%\Thalapathi Studio\`
(`paths.get_app_data_dir()`), a per-user folder that's always writable
regardless of where the app itself is installed, created automatically
if it doesn't exist. On first run, if a file already exists at the *old*
location (next to `main.py` in development, or next to the `.exe` when
built) but nothing exists yet at the new location, it's **copied** -
never moved - into place, so nothing is ever lost and the original is
left untouched. Once a file exists at the new location, it's never
overwritten or re-copied.

`ShopTracker.spec` needed no structural changes - it already builds in
onedir mode (`EXE(exclude_binaries=True)` + `COLLECT(...)`), which is
exactly what `dist\Thalapathi Studio\Thalapathi Studio.exe` requires;
only its explanatory comment was updated, since it previously (and now
incorrectly) described the database as living next to the .exe.

**Tests performed** (all against the real database/app_settings/paths
code, not just read through):
- Simulated a pre-existing development database and settings file "next
  to the app," then imported the app fresh - confirmed both were copied
  into the new location, confirmed the copied data is byte-correct, and
  confirmed the **original files were left completely untouched**.
- Modified the new-location database directly (simulating real use after
  migration), then re-imported - confirmed it does **not** re-copy or
  overwrite from the old location a second time.
- **Made the entire application folder read-only** (`chmod -w`,
  simulating a real `C:\Program Files\` install with no write
  permission) and ran a full app initialization - `init_db()`, a
  database connection, and a settings write all succeeded, proving the
  app never needs write access to its own install folder.
- Verified the exact Windows path string format
  (`%LOCALAPPDATA%\Thalapathi Studio\shop_tracker.db`) using Windows
  path-join semantics directly, since this sandbox itself is Linux.
- Ran your full 9-item test list end-to-end using two genuinely separate
  process launches (Qt only allows one running application per process,
  so "close and reopen" was tested as two real, independent process
  starts, not just re-reading a variable in the same process): app
  starts, login works, all pages navigate, a transaction was created,
  the app closed, a **fresh process** reopened it, the transaction was
  still there, the theme choice (set to Dark before closing) was still
  applied, and the database was confirmed to be in the new location both
  times.
- Re-ran the existing Worker-privacy and Admin cross-visibility checks
  to confirm this change didn't affect them.

Five focused corrections on top of the existing, working application.
No rebuild, no data loss, no unrelated changes.

## 1. Premium UI refresh

Switched from the plain dark theme to a fresh, misty green/teal premium
theme (`theme.py`), inspired by the tea-garden reference image's
feeling - never used as a literal background. Soft gradient sidebar and
login background, white rounded cards with a subtle drop shadow on the
login card, teal-green accent buttons with hover states, clean tables.

**A real bug found and fixed along the way:** rendering actual
screenshots (not just reading the QSS) revealed that `QLabel` - which is
secretly a subclass of `QFrame` in Qt - was inheriting a faint background
box from the global card-styling rule whenever a label had its own
`setStyleSheet("color: ...")` call without an explicit `QLabel { }`
selector. This was invisible on the old dark theme (no visible border
was ever set) but became visible on the new light theme. Fixed on the
highest-visibility screens (login, header) by scoping those calls
explicitly; softened at the theme level for the rest of the app. See
"Remaining limitations" below.

## 2. Settings restructure

New `ui/settings_window.py` replaces the old bare Change-PIN-only
Settings page:
- **Account Details**: Name, Username, Role, Account Status
- **Change PIN**: identical screen and logic for Worker and Admin -
  nothing here is role-restricted
- **Log Out**: returns to the login screen without closing the app

There was no duplicate Change PIN location to remove (Worker
Management's "Reset PIN" is Admin resetting *someone else's* PIN, a
different and still-necessary feature).

## 3. Renamed to Thalapathi Studio 💻

Updated everywhere user-facing: login screen (title + window title),
main window title and header logo, every sub-screen's window title, and
the PyInstaller spec's output name. Internal Python file/module names
were deliberately left alone (e.g. `main.py`, `database.py`) per your
instruction not to risk breaking imports for a cosmetic rename.

## 4. Daily Closing wording simplified

Labels only - **zero changes to the calculation logic**:
- Opening Cash → **Cash in Drawer at Start**
- Expected Cash → **Cash That Should Be in Drawer**
- Actual Cash → **Cash Actually in Drawer**
- Difference → **Cash Difference**
- "Save Daily Closing" → **Finish Today's Closing**

Added one plain-language subtitle under the heading. Left "Cash Sales,"
"UPI Sales," "Cash Expenses," and the "Cash matches" / "difference
detected" messages unchanged since they were already clear.

## 5. Fixed service rates — enforced on the backend, not just hidden in the UI

This was the most important item, so here's exactly what changed:
- `database.create_transaction()` **no longer accepts a `rate` parameter
  at all.** It looks the current price up itself from the `services`
  table using `service_id` - there is no argument through which any
  caller (this screen or anything else) could submit a different price.
- `ui/job_entry_window.py`'s Rate field is now a plain read-only label,
  not a spinbox - there is nothing for a worker to type into.
- Added a `refresh()` method to the New Job screen so a rate change
  Admin makes in Service Management shows up immediately, even if a
  worker already had New Job open (pages are created once and reused).
- Confirmed old transactions keep their originally-stamped rate/amount
  even after Admin changes a service's current rate.

## Files changed this pass

New: `ui/settings_window.py`.
Rewritten: `theme.py`, `ui/login_window.py`, `ui/job_entry_window.py`.
Modified: `database.py` (create_transaction signature, get_user_by_id
added), `ui/main_window.py` (Settings page wiring, sidebar width,
branding, label fix), `ui/daily_closing_window.py` (wording),
`ShopTracker.spec` (output name).

## How to run this on Windows

```
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
No new dependencies.

## Tests actually performed (all against the shipped files)

- **Test 1** (Worker creates New Job): confirmed the Rate field is a
  `QLabel`, not an editable widget; confirmed it auto-fills from the
  selected service; confirmed the total calculates correctly; confirmed
  the job saves.
- **Test 2** (backend rejects a bypassed rate): confirmed via
  `inspect.signature()` that `rate` isn't even a parameter anymore, and
  that attempting to pass one raises `TypeError`.
- **Test 3** (Admin changes rate): changed Xerox B&W from its original
  rate to a new one, confirmed a worker's *already-open* New Job page
  shows the new rate after `refresh()`, confirmed the new job's amount
  uses the new rate, and confirmed the earlier job's stored amount and
  rate are byte-for-byte unchanged.
- **Test 4 & 5** (Change PIN, both roles): changed Worker 1's PIN via
  Settings, confirmed the old PIN then fails and the new one works;
  repeated for Admin.
- **Test 6** (Logout): confirmed Settings' Logout button returns to the
  login screen while the Qt application itself keeps running.
- **Test 7** (Daily Closing): confirmed all four relabeled fields render
  with the new wording, and confirmed the actual Rs-for-Rs calculation
  (opening + cash sales − cash expenses = expected; actual − expected =
  difference) is untouched.
- **Test 8** (UI/navigation regression): logged in as both roles and
  clicked through every sidebar page for each (10 for Worker, 13 for
  Admin) with no crash; re-confirmed Worker-to-Worker data privacy still
  holds after all the changes; confirmed data survives an application
  restart; confirmed the (untouched) forced-PIN-change flow after an
  Admin reset still works correctly.

I also rendered actual PNG screenshots of the login screen, both
dashboards, Settings, New Job, and Daily Closing to visually inspect the
redesign rather than just trust the stylesheet - that's how the QLabel
bug above was caught.

## Remaining limitations

- The QLabel/QFrame background-inheritance quirk described in section 1
  is fixed on the login screen and header, but **not swept across every
  other screen** (dashboard cards, management screens, etc.) - doing
  that fully means touching 50+ individual `setStyleSheet(...)` calls
  across the whole project, which felt disproportionate to "make
  focused changes only" for this pass. In practice this shows as a
  faint, barely-visible rectangular tint behind some colored status
  text - not a broken layout - but I want to be upfront that it isn't
  100% eliminated everywhere. Happy to do a dedicated pass if you'd
  like it fully swept.
- Emoji icons in the sidebar (🏠 ➕ 📋 etc.) are drawn using your
  system's emoji font; I can't verify how they render in actual color on
  Windows from this sandbox, only that they display as recognizable
  glyphs here.
- The PyInstaller `.exe` build itself remains unverified (documented
  already as a prior limitation) - this pass only updated its output
  name to match the new branding.
