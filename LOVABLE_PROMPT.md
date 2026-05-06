# Lovable prompt — folder_file UI

Copy everything between the `===` lines into Lovable's prompt box.

===

Build a single-page React + Tailwind app called **folder_file**. It's a control panel for a small Python program that runs on the user's own computer and downloads attachments from their email. The Python program exposes a REST API at `http://127.0.0.1:8765` — the UI talks to that. CORS is already configured on the backend to allow Lovable origins.

## What the app does (one-liner)

User connects an email account (Gmail OAuth, Microsoft OAuth, or IMAP+app-password), picks a folder in their mailbox, picks a naming prefix and which file types to download, picks an output folder on their PC, and clicks **Run**. The backend streams progress; the UI shows the saved filenames as they appear.

## Tech & style

- React, TypeScript, Tailwind, shadcn/ui components.
- Single-page layout. Sidebar with Accounts list on the left; main panel with the current step on the right.
- Clean, modern, friendly — light theme, soft slate/white background, indigo accents.
- Use `lucide-react` icons. Header has a small "folder_file" wordmark and a connection-status dot ("API: connected" / "API: offline" by polling `/healthz` every 5s).
- All API calls go to a configurable base URL. Default: `http://127.0.0.1:8765`. Show a small gear icon in the header to change it (saved in `localStorage`).
- Use `fetch` with `credentials: 'omit'`. Handle errors with toast notifications.

## Screens / flow

There is no router — it's a single page that progresses through these states based on what the user has selected.

### 1. Accounts panel (always visible, left sidebar)

- Heading: "Accounts"
- Three buttons: **Connect Gmail** (Google G icon), **Connect Microsoft** (Microsoft squares icon), **Add IMAP (app password)** (key icon)
- Below: list of saved accounts. Each row shows provider icon, email, auth-type badge ("OAuth" green / "Password" gray), and a trash icon to delete.
- Selecting an account row makes it the "active account" (highlight it; persist active id to localStorage).
- Polls `GET /accounts` every 5s while no OAuth flow is in progress, every 1.5s during an OAuth flow.

### 2. Run config (main panel, only when an account is selected)

Form with these fields, in this order:

1. **Folder** — `<Select>`. On account selection, fetch `GET /accounts/{id}/folders` and populate. Loading state. If the call fails, show an inline retry button.
2. **Naming prefix** — `<Input>`. Validate: `^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$`. Helper text under it: "Files will be saved as `<prefix>_001.<ext>`, `<prefix>_002.<ext>`, ..."
3. **File types** — multi-select chips. Pre-populate from `GET /providers` `common_extensions`. Plus an "Add custom..." input that accepts comma-separated extensions. Chips toggle on click. If none selected, show a warning chip "All attachment types".
4. **Output folder (on your PC)** — `<Input>`. Default value: `C:\\Users\\<you>\\Downloads\\<prefix>`. Helper text: "This is a path on the machine running the local server."
5. **After download** — radio group: "Leave email alone" (default, recommended) / "Delete from server" (red text warning: "Permanent. Use only on a folder you're comfortable emptying.").

Footer of the form has two buttons: **Run once** (primary) and **Reset counter for this folder** (secondary, ghost). Reset calls `POST /accounts/{id}/state/reset?folder=<folder>`.

### 3. Job progress (modal or inline drawer that opens after Run)

After clicking Run:

1. `POST /run` with the form payload, get `{ job_id }`.
2. Poll `GET /jobs/{job_id}` every 800ms.
3. Show:
   - Status pill: queued / running / done / error (color-coded).
   - Big counter: "**N files saved**" with subtle pulse while running.
   - Streaming log: a scrollable monospaced list of `log[]` lines (auto-scroll to bottom).
   - When status is `done`: green check, message "Done. {saved} file(s) saved.", a "Run again" button and a "Close" button.
   - When status is `error`: red icon, the `error` field as the message, "Try again" button.

## OAuth flows (this is the trickiest part — implement carefully)

### Gmail flow:

1. User clicks **Connect Gmail**.
2. UI calls `POST /auth/gmail/start`. Response: `{ auth_url, state }`.
3. UI opens `auth_url` in a centered popup window: `window.open(auth_url, "ff_oauth", "width=520,height=720")`.
4. UI immediately starts polling `GET /accounts` every 1.5s.
5. The user signs in with Google in the popup. Google redirects the popup to `http://127.0.0.1:8765/auth/gmail/callback?code=...&state=...`. The local backend handles that redirect itself and returns an HTML success page in the popup. The user closes the popup (or it can be auto-closed).
6. The new account appears in the next `GET /accounts` poll. Show a success toast: "Connected eric@gmail.com". Stop the polling (revert to 5s).
7. If 90 seconds elapse with no new account and the popup is closed, show an inline error: "Didn't see a new account. Check the popup for an error and try again."

### Microsoft flow:

Same as Gmail except `POST /auth/microsoft/start` and the popup completes via the Microsoft callback. Identical UI behavior.

### IMAP + app password flow:

Modal with three fields: email, app password, and (optional) IMAP host + port. On submit, `POST /accounts/password` with `{ email, password, imap_host?, imap_port? }`. On success, show toast and add to list. On error, show inline error from the response `detail` field.

The modal should include a small expandable "Where do I get an app password?" section with three links:
- Gmail: https://myaccount.google.com/apppasswords
- Outlook: https://account.microsoft.com/security
- iCloud: https://account.apple.com

## API contract (verbatim)

Base URL: `http://127.0.0.1:8765` (configurable, persisted in localStorage).

```
GET  /healthz                                    -> { ok: bool, version: string }
GET  /providers                                  -> { common_extensions: string[],
                                                       imap_hints: { domain, host, port }[] }

GET  /accounts                                   -> { accounts: Account[] }
DELETE /accounts/{id}                            -> { ok: true }
GET  /accounts/{id}/folders                      -> { folders: string[] }
GET  /accounts/{id}/state                        -> { entries: { [key: string]: { last_uid, counter } } }
POST /accounts/{id}/state/reset?folder=<name>    -> { ok: true }

POST /accounts/password
     body: { email, password, imap_host?, imap_port? }
     -> Account

POST /auth/gmail/start                           -> { auth_url, state }
POST /auth/microsoft/start                       -> { auth_url, state }
(callbacks are handled directly by the backend; UI does not call them)

POST /run
     body: {
       account_id: string,
       folder: string,
       prefix: string,
       allowed_exts: string[],   // each like ".pdf"
       output_dir: string,
       post_action: "leave" | "delete"
     }
     -> { job_id: string }

GET  /jobs                                       -> { jobs: Job[] }
GET  /jobs/{id}                                  -> Job

type Account = {
  id: string;          // e.g. "gmail:eric@gmail.com"
  provider: "gmail" | "microsoft" | "imap";
  email: string;
  imap_host: string;
  imap_port: number;
  auth_type: "oauth" | "password";
  display_name?: string | null;
  extras?: Record<string, unknown>;
}

type Job = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  log: string[];
  files: string[];
  saved: number;
  deleted: number;
  error: string | null;
  started_at: number | null;
  ended_at: number | null;
}
```

## Empty / error states

- **API offline** (any fetch fails on /healthz for 10s): big inline card on the right panel that says "Local server not running. Start it with `python -m folder_file.server` and then refresh." with a copy-to-clipboard button for that command.
- **No accounts**: in the right panel, show a centered illustration + "Connect an email account on the left to get started."
- **No folders returned**: in the folder dropdown, "No folders found. Try reconnecting the account."
- **Output folder rejected by backend** (400): inline error under the field.

## Polish details

- Disable the **Run** button if any required field is empty/invalid; show what's missing.
- Persist last-used (folder, prefix, allowed_exts, output_dir, post_action) per account in localStorage so re-opens are instant.
- Keyboard: Enter submits the form when no other element has focus.
- Show the file path of the saved files as `…\{filename}` (truncate the prefix path on the left).

That's everything. Build it.

===

## After Lovable generates it

1. In Lovable, set the API base URL to `http://127.0.0.1:8765` (the gear icon).
2. On your PC: `cd folder_file && .venv\Scripts\activate && python -m folder_file.server`.
3. Open the Lovable preview URL — it should show the connection dot as green.
4. Connect an account.
5. Run.

Note on browsers + private network: modern Chrome treats `https://*.lovable.app -> http://127.0.0.1` as a "private network access" call. The first time, you may see a Chrome prompt asking permission. Allow it. Firefox does not require this prompt.
