folder_file — quick start
=========================

What this is
------------
A small Windows app that connects to your email, walks a folder you
choose (e.g. the "Aria" folder in your Outlook inbox), and saves all
the pictures and attachments from it to your computer with names like
Aria_001.jpg, Aria_002.jpg, ...

Re-running it later only pulls the NEW stuff since last time.

All your data stays on your computer. No cloud, no analytics, no
account required. The app talks to your email provider directly.


First time running it
---------------------
1. Windows will say "Windows protected your PC" because the app isn't
   code-signed (that costs $300/year just to remove this dialog).

   Click "More info" -> "Run anyway".

   You only see this once.

2. A small folder icon appears in your system tray (lower-right corner
   of the screen, near the clock — you may need to click the up-arrow
   to see it). That's the app running.

3. Your browser opens to http://127.0.0.1:8765 showing the control
   panel. If it doesn't, right-click the tray icon -> "Open folder_file".


Using it
--------
1. Click "Add IMAP" (easiest), "Connect Gmail", or "Connect Microsoft"
   to sign in to your email.

   - Gmail / Outlook: regular sign-in flow in your browser.
   - IMAP: needs an "app password" from your email provider (Gmail
     and iCloud both support this; personal @outlook.com doesn't —
     use "Connect Microsoft" instead).

2. Pick a folder from your email (e.g. "INBOX/Aria").

3. Type a prefix for filenames (e.g. "Aria") and pick where to save
   the files (default: your Downloads folder).

4. Click "Run once".


To quit
-------
Right-click the tray icon -> "Quit".


Where things live
-----------------
- Saved files: wherever you pointed it at (default: Downloads\<prefix>\)
- Settings + sign-in tokens: %APPDATA%\folder_file\
- Uninstall: Settings -> Apps -> folder_file (if you used the installer),
  or just delete the folder (if you used the zip version).


Trouble?
--------
- Browser shows "site can't be reached": the app didn't start. Try
  re-launching from the Start menu (or double-click folder_file.exe
  again from where you unzipped it).

- Tray icon doesn't appear: it might be hidden. Click the up-arrow in
  your system tray to show hidden icons.

- "Connect Gmail" / "Connect Microsoft" shows a 400 error: the
  OAuth client IDs aren't configured in this build. Use "Add IMAP"
  with an app password instead, or ask Eric for an OAuth-enabled build.

- Anything else: ping Eric.


Made by Eric Ragozin. github.com/Ragozi/folder_file
