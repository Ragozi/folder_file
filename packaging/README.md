# Build & packaging

This directory holds the configs that turn the Python project into shippable
binaries (Windows .exe + macOS .app) and a Windows installer.

## Files

- `folder_file.spec` — PyInstaller config. Bundles Python + all deps + the
  React UI under `src/folder_file/web/` into a single `dist/folder_file/`
  directory. On macOS it additionally produces `folder_file.app`.
- `installer.iss` — Inno Setup script for the Windows installer. Wraps the
  PyInstaller output in a friendly setup wizard with optional desktop shortcut
  and "start at login" toggle.
- `../.github/workflows/release.yml` — CI workflow that runs the whole pipeline
  on every `v*` tag and publishes binaries to GitHub Releases.

## One-time setup before first build

1. **Connect Lovable to GitHub** (creates a separate repo holding the React UI).
2. **Set the `UI_REPO` env var** in `.github/workflows/release.yml` to the URL of
   that repo, e.g. `https://github.com/Ragozi/folder-file-ui`.
3. If the UI repo is private, generate a fine-grained GitHub PAT with
   `Contents: read` on it and add it as repo secret `UI_REPO_TOKEN`.

## Build locally (Windows)

```powershell
# from the repo root
pip install pyinstaller
pyinstaller packaging/folder_file.spec --noconfirm
# output is in dist/folder_file/folder_file.exe
```

To also build the installer (requires Inno Setup):

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
# output is in packaging/Output/folder_file_setup.exe
```

## Build locally (macOS)

```bash
pip install pyinstaller
pyinstaller packaging/folder_file.spec --noconfirm
# output is dist/folder_file/folder_file.app and dist/folder_file/folder_file
```

## Tag a release (CI does the work)

```bash
git tag v0.1.0
git push origin v0.1.0
```

Wait ~10 min, check Actions tab for green, GitHub Releases page will have:
- `folder_file_setup.exe` — Windows installer
- `folder_file-windows.zip` — portable Windows folder
- `folder_file-macos.zip` — portable macOS folder

## SmartScreen on Windows

The .exe is unsigned. First-run users see a SmartScreen warning:
"Windows protected your PC". They click **More info** → **Run anyway**. To
remove this warning permanently you'd need a code-signing certificate
(~$200/yr from Sectigo, DigiCert, etc.). Out of scope for v1.

## Gatekeeper on macOS

Same situation. First-run users right-click the .app → **Open** → **Open**
on the warning dialog. Notarization (~$99/yr Apple Developer Program)
removes the warning. Out of scope for v1.
