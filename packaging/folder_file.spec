# PyInstaller spec for folder_file (cross-platform).
# Build with:
#   pyinstaller build/folder_file.spec --noconfirm
# Output:
#   dist/folder_file/folder_file.exe   (Windows)
#   dist/folder_file/folder_file.app   (macOS, see APP block at bottom)

# ruff: noqa
import sys
from pathlib import Path

block_cipher = None
project_root = Path.cwd()
src_root = project_root / "src" / "folder_file"

datas = [
    (str(src_root / "web"), "folder_file/web"),
]

hiddenimports = [
    # keyring backends — PyInstaller can miss these because they're loaded by name
    "keyring.backends.Windows",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.fail",
    # email package codecs sometimes get pruned
    "email.mime",
    "email.mime.multipart",
    "email.mime.text",
    "email.mime.image",
    "email.mime.application",
    # google-auth uses pkg_resources / importlib_metadata under the hood
    "google.auth.transport.requests",
    "google_auth_oauthlib.flow",
    # msal extensions
    "msal.application",
    "msal.authority",
    # FastAPI / Starlette deps loaded at runtime
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.loops.auto",
    "uvicorn.workers",
]

a = Analysis(
    [str(src_root / "tray.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # cut things we definitely don't need to keep size sane
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PySide6",
        "PyQt5",
        "PyQt6",
    ],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="folder_file",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # no terminal window pops up
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="folder_file",
)

# macOS .app bundle — only used when building on darwin.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="folder_file.app",
        icon=None,                # add an .icns later if you want a custom icon
        bundle_identifier="com.ragozi.folderfile",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": True,  # tray-only app, no Dock icon
        },
    )
