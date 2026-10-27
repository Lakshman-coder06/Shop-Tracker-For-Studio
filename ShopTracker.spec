# ShopTracker.spec
# -----------------
# PyInstaller build spec for producing the "Thalapathi Studio" desktop app
# on Windows. (The .spec file itself keeps its original name - renaming it
# has no effect on the app; only the `name=` values below control what
# the built app and its folder are actually called.)
#
# HOW TO USE (on your Windows machine, inside the activated venv):
#   pip install pyinstaller
#   pyinstaller ShopTracker.spec
#
# The finished .exe appears in dist\Thalapathi Studio\Thalapathi Studio.exe
# Copy the whole "dist\Thalapathi Studio" folder wherever you want to run
# it from - it's self-contained and does not need Python installed on the
# target PC.
#
# NOTE (v11, shared-shop version): the app no longer keeps its own database.
# All shop data lives on the shop server (see the ShopTrackerServer folder).
# Only a small app_settings.json (theme + the server's address) is stored
# per PC, in %LOCALAPPDATA%\Thalapathi Studio\ - see paths.py. The app now
# also needs the "requests" package (already in requirements.txt).

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['win32timezone'],  # pywin32 sometimes needs this spelled out explicitly
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Thalapathi Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no black console window behind the app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,       # put a .ico path here if you make a shop logo icon later
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Thalapathi Studio',
)
