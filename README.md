# folder_file

A small local app that connects to your email over IMAP, walks a folder you choose, and saves attachments to your computer with names like `Aria_001.jpg`, `Aria_002.pdf`, ...

Two ways to use it:

- **CLI** (`python -m folder_file`) — interactive prompts, app-password auth.
- **Local API + Lovable UI** (`python -m folder_file.server`) — Gmail / Microsoft OAuth ("Select a Google account…"), web UI built in [Lovable](https://lovable.dev) calls a small FastAPI server running on your PC.

The server runs on `http://127.0.0.1:8765`. Files are written to whichever folder on your PC you point at.

## Install

```powershell
git clone https://github.com/Ragozi/folder_file.git
cd folder_file
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## CLI mode (app password)

```powershell
python -m folder_file
```

Generate an app password first:
- **Gmail** — https://myaccount.google.com/apppasswords (requires 2-step verification)
- **Outlook / M365** — https://account.microsoft.com/security → *Advanced security* → *App passwords*
- **iCloud** — https://account.apple.com → *Sign-in and security* → *App-specific passwords*

## Server mode (OAuth + UI)

```powershell
python -m folder_file.server
# -> folder_file API listening on http://127.0.0.1:8765
```

The server exposes a small REST API. The Lovable frontend talks to it. CORS is open to `*.lovable.app`, `*.lovable.dev`, `*.lovableproject.com`, and `localhost`.

### One-time OAuth client setup

OAuth requires a *client ID* per provider. You register a client once in each provider's developer console and tell the local app about it. Two ways to provide them:

**Option A** — environment variables (recommended for development):

```powershell
$env:GOOGLE_CLIENT_ID = "xxx.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "xxx"
$env:MICROSOFT_CLIENT_ID = "xxx-xxx-xxx-xxx"
python -m folder_file.server
```

**Option B** — drop a JSON file at `%APPDATA%\folder_file\oauth_clients.json`:

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

#### How to get a Google client ID

1. Go to https://console.cloud.google.com → create a new project (any name).
2. **APIs & Services** → **Library** → enable **Gmail API**.
3. **APIs & Services** → **OAuth consent screen** → User type *External* → fill in app name, support email.
   - Scopes step: add `https://mail.google.com/`.
   - Test users: add your own Gmail address (so the unverified-app warning doesn't block you).
4. **Credentials** → **Create credentials** → **OAuth client ID** → **Web application**.
   - Authorized redirect URI: `http://127.0.0.1:8765/auth/gmail/callback`
5. Copy the client ID and client secret into env vars or `oauth_clients.json`.

#### How to get a Microsoft client ID

1. Go to https://portal.azure.com → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Name it anything. Supported account types: *Accounts in any organizational directory and personal Microsoft accounts*.
3. Redirect URI: pick **Web**, set to `http://127.0.0.1:8765/auth/microsoft/callback`.
4. Register. Copy the **Application (client) ID** into env var or `oauth_clients.json`.
5. Under **Authentication** → enable *Allow public client flows* = **Yes**.
6. Under **API permissions** → **Add a permission** → **APIs my organization uses** → search **Office 365 Exchange Online** → Delegated permissions → check `IMAP.AccessAsUser.All` → **Add permissions**.
7. Also add **Microsoft Graph** → Delegated → `offline_access` and `openid` and `email`.

### Connecting an account

The Lovable UI gives you Connect buttons. Behind the scenes:

1. UI calls `POST /auth/gmail/start` (or `microsoft/start`).
2. Server returns `{auth_url}`. UI opens it in a new window.
3. You sign in with Google / Microsoft and grant the IMAP scope.
4. Provider redirects to `http://127.0.0.1:8765/auth/gmail/callback?code=...`.
5. Server exchanges the code for tokens, stores them in Windows Credential Manager, returns a "Connected as ___" page.
6. UI polls `GET /accounts` and shows the new account.

Refresh tokens are stored in keyring; subsequent runs auto-refresh access tokens — no re-prompting until you delete the account.

## API summary

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET    | `/healthz` | Liveness |
| GET    | `/providers` | Common extensions + IMAP host hints |
| GET    | `/accounts` | List saved accounts |
| DELETE | `/accounts/{id}` | Forget account + tokens |
| GET    | `/accounts/{id}/folders` | List IMAP folders |
| GET    | `/accounts/{id}/state` | Show counters per folder |
| POST   | `/accounts/{id}/state/reset?folder=...` | Reset counter for a folder |
| POST   | `/accounts/password` | Add an IMAP+password account |
| POST   | `/auth/gmail/start` | Begin Gmail OAuth |
| GET    | `/auth/gmail/callback` | OAuth redirect (used by Google) |
| POST   | `/auth/microsoft/start` | Begin Microsoft OAuth |
| GET    | `/auth/microsoft/callback` | OAuth redirect (used by Microsoft) |
| POST   | `/run` | Submit a sweep job |
| GET    | `/jobs` | Recent jobs |
| GET    | `/jobs/{id}` | Job status + log |

`POST /run` body:
```json
{
  "account_id": "gmail:eric.ragozin@gmail.com",
  "folder": "INBOX/Aria",
  "prefix": "Aria",
  "allowed_exts": [".pdf", ".jpg", ".jpeg", ".png"],
  "output_dir": "C:\\Users\\erago\\Downloads\\Aria",
  "post_action": "leave"
}
```

`GET /jobs/{id}` response:
```json
{
  "id": "ab12...",
  "status": "running",
  "saved": 2,
  "deleted": 0,
  "files": ["...\\Aria_001.jpg", "...\\Aria_002.jpg"],
  "log": ["  Aria_001.jpg  <- 'Vacation pics' (2026-04-12)", "..."],
  "error": null
}
```

## Tests

```powershell
pytest
```
