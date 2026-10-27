# Thalapathi Studio – shared shop version (v11)

## What was wrong, and what changed

Before, each computer kept its **own private database**. Worker 1's PC, Worker 2's PC
and the Admin's PC could never see each other's jobs.

Now there is **one shared database on one computer – the "server"** – and every PC's
app connects to it. Same screens as before. Workers still see only their own work;
Admin sees everything.

```
  Worker 1's PC ──┐
  Worker 2's PC ──┼──►  SHOP SERVER (one PC)  ──►  the one real database + backups
  Admin's PC    ──┘
```

This zip has two folders:

| Folder | What it is | Where it goes |
|---|---|---|
| `ShopTrackerServer` | the server | **ONE** computer only |
| `ShopTracker` | the app (your screens) | **every** computer: workers and Admin |

---

## Step 1 – Set up the server (once, on one PC)

Pick a PC that is switched on whenever the shop is working (it can also be a normal
work PC). If it is off, nobody can record anything.

1. Install **Python 3.10 or newer** from python.org. On the first install screen, tick
   **"Add python.exe to PATH"**.
2. Copy the `ShopTrackerServer` folder onto that PC (e.g. to `C:\ShopTrackerServer`).
3. Double-click **`run_server.bat`**. The first time it installs what it needs (about a
   minute, needs internet).
4. Windows may ask to allow it through the firewall. Choose **Allow** for **Private
   networks**.
5. The window prints one or more addresses like `http://192.168.1.20:8000`. **That is
   the address you will type into each app.** Leave the window open.
6. In Windows power settings, set the server PC to **never sleep**.

To start automatically with Windows: press `Win + R`, type `shell:startup`, and put a
shortcut to `run_server.bat` in that folder.

## Step 2 – Set up each PC (workers and Admin)

1. Copy the `ShopTracker` folder to the PC.
2. Install the requirements once (`pip install -r requirements.txt`) and run
   `python main.py` – exactly as before. (If you build an `.exe` with
   `pyinstaller ShopTracker.spec`, copy that to the PCs instead.)
3. The first time, the app asks for the **server address**. Type the address from
   Step 1, click **Test connection** (it should say ✓ Connected), then **Save**.
   You can change it later from the small **"Server: …"** link on the login screen.
4. Log in.

**Starter accounts** on a brand-new server: Worker 1 / 1111, Worker 2 / 2222,
Worker 3 / 3333, Admin / 9999. Each one is **forced to choose a new PIN the first time
it logs in.** Do this first: log in as Admin, then use *Worker Management* to add your
real workers and switch off any starter accounts you don't need.

All PCs must be on the **same Wi-Fi/network as the server PC** (unless you set up
remote access below).

## Keeping data you already have

If one of your existing PCs has real data you want to keep, copy its file
`%LOCALAPPDATA%\Thalapathi Studio\shop_tracker.db` into the server's `data` folder
**before the first start** (create the folder if it doesn't exist). Its jobs and the
PINs people already chose carry over.

Only **one** PC's data can be brought in this way. The old databases can't be merged
automatically, because each started numbering its records from 1. After you confirm
everything works, the old file on each PC is simply unused; keep it as a spare copy.

## Admin checking from home (remote access)

The server address only works on the shop network by default. Two ways to reach it from
elsewhere:

- **Easiest: a private-network tool such as Tailscale.** Install it on the server PC and
  on the Admin's device, sign in to the same account, and use the server PC's Tailscale
  address in the app (e.g. `http://100.x.x.x:8000`). Nothing is exposed to the public
  internet. (It has a free personal plan; check their current terms.)
- **A cloud server.** The `Dockerfile` in `ShopTrackerServer` is provided for this. It
  **must** have a persistent disk mounted at `/data`; without one, the database is erased
  whenever the host restarts. Free cloud tiers often don't include one. I have not been able
  to test this route, so treat it as a starting point.

**Please do not** open the server's port on your router to the internet. The shop network
connection is not encrypted (plain `http`). That is fine on your own Wi-Fi, but PINs would be
readable over the internet.

## Backups – please read

The server saves a full copy of the database **at every start and every 12 hours**, into
`ShopTrackerServer\data\backups` (the newest 30 are kept).

Those copies are on the **same disk** as the live database. If that PC's disk fails you lose
both. So **once a week, copy the `backups` folder to a USB drive or cloud drive.**

To restore: close the server window, copy a backup file over
`data\shop_tracker.db` (renaming it to that), and start the server again.

## Things to know

- **No offline mode.** If the server can't be reached, the app says so clearly and does **not**
  save. It shows a red "Offline" light in the header and reconnects by itself. Nothing is saved
  secretly and sent later.
- **Never run two servers** at once for the same shop – the records would split again.
- **Time:** the server keeps Indian time on cloud hosts. On a Windows server PC, make sure the
  PC's own time zone is India Standard Time, because "today's sales" follow that clock.
- **Wrong PIN 5 times** pauses that login for 5 minutes (it stops people guessing 4-digit PINs).
  Restarting the server clears the pause.
- **PINs** must be 4 to 8 characters.
- Two accounts can no longer share a name (the old app allowed it, and the second could never log in).

## If something doesn't work

| What you see | Try this |
|---|---|
| "Can't reach the shop server" | Is the server window open? Is this PC on the same Wi-Fi? Click *Server: …* on the login screen and press **Test connection**. |
| Test works on the server PC but not on others | Windows Firewall on the server PC: allow Python/`run_server.bat` on **Private** networks. |
| "Not a Thalapathi Studio server" | The address is wrong (a router page or another program answered). Re-check it, including `:8000`. |
| "different versions" | Copy the same release's `ShopTracker` folder to that PC. |
| "Your login has expired" | Just log in again (logins last 14 hours, or until an account is switched off). |

Server messages are also written to `ShopTrackerServer\data\logs\server.log`.

## What I could and could not test

Everything was run on Linux, against a real server, driving your **actual app screens**
(headless): three separate "PCs" (Worker 1, Worker 2, Admin) sharing one server; server switched
off mid-save and back on; account switched off while logged in; PIN guessing; 30 simultaneous saves;
old-data import; backups.

**Not tested** (needs a real Windows machine): `run_server.bat`, the Windows firewall prompt, the
real foreground-window activity tracking, building the `.exe`, the cloud `Dockerfile`, and speed
over a slow or remote connection. Expect these to work, but confirm them on your own PCs, and tell
me exactly what you see if anything misbehaves.
