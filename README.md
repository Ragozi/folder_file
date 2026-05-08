# folder_file

A small desktop app that connects to your email, walks a folder you choose (e.g. `INBOX/Aria`), and saves all the attachments and pasted-in pictures from that folder to your computer with sequential names like `Aria_001.jpg`, `Aria_002.pdf`, ...

Designed for one specific job: pulling years of pictures out of email folders into a real folder on your PC.

- Works with **Outlook / Microsoft 365** (OAuth — "Sign in with Microsoft").
- Works with **Gmail** (OAuth — "Sign in with Google").
- Works with **any IMAP provider** via app password (iCloud, FastMail, generic IMAP).
- Saves both **regular attachments** AND **embedded pictures** (the kind you paste into the email body) — with independent filters for each source.
- Continues numbering across runs (re-running pulls only new pictures).

[Latest release →](https://github.com/Ragozi/folder_file/releases/latest)

## Quick start (just want to use it)

1. Go to [Releases](https://github.com/Ragozi/folder_file/releases/latest) and download:
   - **Windows** → `folder_file_setup.exe` (recommended — proper installer with Start menu shortcut), or `folder_file-windows.zip` (portable, just unzip and double-click).
   - **Mac** → `folder_file-macos.zip`. Unzip, drag `folder_file.app` to Applications.

2. **First-launch warning:** the app isn't code-signed (would cost ~$300/yr just for that). When you double-click for the first time:
   - **Windows SmartScreen:** "Windows protected your PC" → click *More info* → *Run anyway*.
   - **macOS Gatekeeper:** right-click the .app → *Open* → *Open* on the warning dialog.
   You only have to do this on first launch.

3. The browser opens to `http://127.0.0.1:8765` showing the control panel. A small folder icon also appears in your system tray (Windows) or menu bar (Mac) — that's where the app lives.

4. Connect an email account. **Three ways**, listed easiest-first:

   | Path | What you do | OAuth setup needed |
   |---|---|---|
   | **IMAP + app password** | Click *Add IMAP*, paste email + 16-char app password | None |
   | **Gmail OAuth** | Click *Connect Gmail*, sign in | Yes — see below |
   | **Microsoft OAuth** | Click *Connect Microsoft*, sign in | Yes — see below |

5. Pick a folder, type a prefix (e.g. `Aria`), choose what to download, click **Run once**.

6. To quit, right-click the system-tray icon → **Quit**.

State and tokens live in `%APPDATA%\folder_file\` (Windows) or `~/Library/Application Support/folder_file/` (Mac). Files you download go to whatever output folder you point at — usually `Downloads\<prefix>\`.

## Generating an app password (the no-OAuth-setup path)

Most providers require 2-step verification before app passwords appear in their UI.

| Provider | Where |
|---|---|
| Gmail | https://myaccount.google.com/apppasswords (needs 2-step verification on) |
| Outlook personal | **Likely won't work** — Microsoft has disabled basic-auth IMAP on personal `@outlook.com` accounts. Use Microsoft OAuth instead. |
| Microsoft 365 (work) | Your tenant admin's MFA / app-password page if enabled |
| iCloud | https://account.apple.com → Sign-In and Security → App-Specific Passwords |
| FastMail | Settings → Password & Security → App Passwords |

If your provider's IMAP server isn't auto-detected from the email domain, you can supply the host/port manually in the *Add IMAP* modal.

## Gmail OAuth setup (one-time, ~5 min)

The OAuth flow needs a Google Cloud project. This is per-user — each person who installs folder_file needs their own client ID, OR you (the distributor) can ship one with the app.

1. https://console.cloud.google.com → *Create project* (any name).
2. **APIs & Services** → **Library** → enable **Gmail API**.
3. **APIs & Services** → **OAuth consent screen** → *External* → fill in app name, support email.
   - Scopes step: add `https://mail.google.com/`.
   - Test users: add the Gmail address you'll be reading from.
4. **Credentials** → **+ Create credentials** → **OAuth client ID** → **Web application**.
   - Authorized redirect URI: `http://127.0.0.1:8765/auth/gmail/callback`
5. Copy the client ID and secret. Set them via env vars or `oauth_clients.json` (see *Configuring OAuth client IDs* below).

## Microsoft OAuth setup (one-time, ~10 min)

Required for personal `@outlook.com` accounts since Microsoft disabled basic-auth IMAP for them.

1. https://portal.azure.com → search **App registrations** → **+ New registration**.
2. Name it anything. **Supported account types**: pick *"Accounts in any organizational directory and personal Microsoft accounts"*.
3. **Redirect URI**: pick **Mobile and desktop applications** (NOT Web — Azure rejects `http://` for the Web platform). Add: `http://localhost:8765/auth/microsoft/callback`.
4. Click **Register**. On the overview page, copy the **Application (client) ID**.
5. Left sidebar → **Authentication** → scroll down → **Allow public client flows** = **Yes** → Save.
6. Left sidebar → **API permissions** → click **+ Add a permission** → **Microsoft Graph** → **Delegated permissions** → check `offline_access`, `openid`, `email` → Add permissions.
   - The `IMAP.AccessAsUser.All` scope is requested at sign-in time and doesn't need to be pre-added (Office 365 Exchange Online doesn't show in the picker for personal-account-only registrations — that's expected).

## Configuring OAuth client IDs

The app reads OAuth client credentials from one of two places, in order:

**Environment variables** (most useful for development):

```powershell
$env:GOOGLE_CLIENT_ID = "xxx.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "xxx"
$env:MICROSOFT_CLIENT_ID = "xxx-xxx-xxx-xxx"
```

**`oauth_clients.json` file** (for the bundled app):

Create a file at `%APPDATA%\folder_file\oauth_clients.json` (Windows) or `~/Library/Application Support/folder_file/oauth_clients.json` (Mac):

```json
{
  "google": {
    "client_id": "xxx.apps.googleusercontent.com",
    "client_secret": "xxx"
  },
  "microsoft": {
    "client_id": "xxx-xxx-xxx-xxx"
  }
}
```

Restart the app after creating/editing this file.

If a provider's client config is missing, that provider's *Connect* button in the UI will show a 400 error explaining what's missing — IMAP+password still works without any OAuth setup.

## Embedded vs. attached: how the filter works

The app distinguishes two sources of pictures in a single email:

- **Embedded pictures** — images pasted into the email body (Outlook "insert picture inline", drag-drop into compose). These are MIME parts referenced by `cid:` from the HTML body.
- **File attachments** — files added via *Attach file* / drag-drop into the attachments tray.

The Run config has independent toggles + extension filters for each. Examples:
- "Pull only embedded pictures, ignore attached PDFs": Embedded ON (`.jpg .png .heic`), Attachments OFF.
- "Pull all attachments and embedded pics": both ON.
- "Pull only attached PDFs": Embedded OFF, Attachments ON (`.pdf`).

What's NOT extracted: external `<img src="https://...">` URLs in the HTML body (iCloud share links, Google Photos albums) — those bytes don't live in the email and would require a separate fetch.

## Running from source (developers)

```powershell
git clone https://github.com/Ragozi/folder_file.git
cd folder_file
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest

# Three ways to launch:
python -m folder_file              # interactive CLI (app password only)
python -m folder_file.server       # API server, no tray icon, no auto-browser
python -m folder_file.tray         # tray app: API + browser + tray icon
```

## API reference

The packaged app is a small FastAPI server at `http://127.0.0.1:8765` plus a React UI at the same origin. The UI is in a separate repo: [Ragozi/folder-file-ui](https://github.com/Ragozi/folder-file-ui).

| Method | Path | Purpose |
|---|---|---|
| GET    | `/healthz` | Liveness probe |
| GET    | `/providers` | Common extensions + IMAP host hints |
| GET    | `/accounts` | List saved accounts |
| DELETE | `/accounts/{id}` | Forget account + tokens |
| GET    | `/accounts/{id}/folders` | List IMAP folders |
| GET    | `/accounts/{id}/state` | Counter + last-UID per folder |
| POST   | `/accounts/{id}/state/reset?folder=...` | Reset counter for a folder |
| POST   | `/accounts/password` | Add IMAP+password account |
| POST   | `/auth/gmail/start` | Begin Gmail OAuth → returns `{auth_url}` |
| GET    | `/auth/gmail/callback` | OAuth landing page (called by Google) |
| POST   | `/auth/microsoft/start` | Begin Microsoft OAuth |
| GET    | `/auth/microsoft/callback` | OAuth landing page (called by Microsoft) |
| POST   | `/run` | Submit a sweep job (returns `{job_id}`) |
| GET    | `/jobs` | Recent jobs |
| GET    | `/jobs/{id}` | Job status + streaming log |

`POST /run` body:
```json
{
  "account_id": "microsoft:eric@outlook.com",
  "folder": "INBOX/Aria",
  "prefix": "Aria",
  "output_dir": "C:\\Users\\erago\\Downloads\\Aria",
  "post_action": "leave",
  "include_embedded": true,
  "embedded_exts": [".jpg", ".jpeg", ".png", ".heic"],
  "include_attachments": true,
  "attachment_exts": [".jpg", ".jpeg", ".png", ".heic", ".pdf"]
}
```

## Building installers from source

See [`packaging/README.md`](packaging/README.md) for PyInstaller and Inno Setup details, or just push a `vX.Y.Z` tag to trigger the GitHub Actions release workflow.

## Privacy and security

- **All data stays on your computer.** The app talks to your email provider directly over IMAP. No third-party server, no analytics, no telemetry.
- **OAuth refresh tokens** live in `%APPDATA%\folder_file\secrets\` as JSON files (Windows user-account scoped — same trust boundary as your Documents folder).
- **App passwords** are stored the same way.
- **Per-folder state** (last UID + counter) lives in `%APPDATA%\folder_file\state.json` so re-runs only fetch new emails.
- The app **never deletes emails by default**. The "Delete from server" option is opt-in, per-run, and confirmation-required.

## Project layout

```
folder_file/
├── src/folder_file/
│   ├── api.py              # FastAPI app + routes
│   ├── tray.py             # tray-app launcher (entry point for the .exe / .app)
│   ├── server.py           # plain HTTP server entry point (for dev)
│   ├── cli.py              # interactive CLI (legacy, no UI)
│   ├── runner.py           # sweep orchestrator
│   ├── downloader.py       # extract + classify + filter + save
│   ├── imap_client.py      # IMAP wrapping (LOGIN + XOAUTH2)
│   ├── connector.py        # bridges Account → IMAP connection (with token refresh)
│   ├── accounts.py         # account store + file-backed token storage
│   ├── oauth/gmail.py      # Google OAuth flow + token refresh
│   ├── oauth/microsoft.py  # MSAL OAuth flow + token refresh
│   ├── state.py            # per-folder counter + last-UID persistence
│   ├── jobs.py             # async job manager (background sweep threads)
│   ├── config.py           # paths, scopes, IMAP host hints
│   └── web/                # populated at build time with the React UI
├── tests/                  # pytest suite (41 tests, no network)
├── packaging/
│   ├── folder_file.spec    # PyInstaller config (cross-platform)
│   └── installer.iss       # Inno Setup script for Windows installer
├── .github/workflows/
│   └── release.yml         # CI: builds on every v* tag
└── pyproject.toml
```

## License

MIT.
