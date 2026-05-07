# Lovable update prompt — split embedded vs attached

Paste everything between the `===` lines into Lovable.

===

Update the **Run download** form to give the user separate controls for **embedded pictures** (cid:-referenced images pasted into a message body) and **file attachments** (files added via "Attach file"). They're now distinct in the backend and need distinct filters in the UI.

## Backend API changes (already shipped)

`POST /run` body changed. The single `allowed_exts` field is replaced by four new fields. Old field is still accepted for backwards compat but the UI should send the new shape.

**New body:**
```ts
{
  account_id: string,
  folder: string,
  prefix: string,
  output_dir: string,
  post_action: "leave" | "delete",

  include_embedded: boolean,
  embedded_exts: string[],     // each like ".jpg"; empty = all extensions

  include_attachments: boolean,
  attachment_exts: string[],   // empty = all extensions
}
```

If both `include_embedded` and `include_attachments` are false, the API returns 400. Validate client-side and disable the Run button in that state.

`Job.log` lines now contain a `[embed]` or `[attach]` tag, e.g.
```
  Aria_001.jpg [embed] <- 'Vacation pics' (2026-04-12)
  Aria_002.pdf [attach] <- 'Vacation pics' (2026-04-12)
```
No code change needed on the UI side — they're just plain text strings, render as-is.

## UI changes

Replace the existing **File types** section (single chip grid + custom input) with two parallel sections under a shared heading **What to download**.

### Section 1 — "Embedded pictures"

Subtitle: *"Images pasted or dragged into the email body."*

- A toggle switch at the top: **Include embedded pictures** (default ON).
- When ON, show a chip multi-select. Default-checked chips: `.jpg`, `.jpeg`, `.png`, `.heic`. Available chips also include `.gif`, `.webp`, `.bmp`, `.tiff`. Plus an **Add custom...** input that accepts comma-separated extensions and adds them as chips.
- When the chip list is empty, show a small warning chip "All image types" — meaning no extension filter.
- When the toggle is OFF, hide the chips entirely (or render them disabled/grey).

### Section 2 — "File attachments"

Subtitle: *"Files attached via 'Attach file' / drag-drop into the attachments tray."*

- Toggle: **Include attachments** (default ON).
- Default-checked chips: `.pdf`, `.docx`, `.xlsx`, `.zip`. Available chips also include `.jpg`, `.jpeg`, `.png`, `.heic`, `.txt`, `.csv`, `.pptx`. Plus **Add custom...**.
- Empty list → "All attachment types" warning chip.
- OFF → hide chips.

### Validation

- If both toggles are OFF, the **Run once** button is disabled and the missing-fields hint says "Select at least one of embedded or attachments."
- All other validation rules (folder selected, prefix valid, output_dir non-empty) stay the same.

### State persistence

Persist the per-account last-used values in localStorage under the existing scheme. Add the four new keys: `includeEmbedded`, `embeddedExts`, `includeAttachments`, `attachmentExts`. Migrate any old `allowedExts` value: copy it into both `embeddedExts` and `attachmentExts`, then delete the old key.

### Endpoint discovery

The list of common extensions returned by `GET /providers` is still `common_extensions: string[]`. Use it to populate both chip grids — but split visually into image-ish vs other-ish if you want a nice default grouping. (Image-ish: `.jpg, .jpeg, .png, .heic, .gif, .webp, .bmp, .tiff`. Other: everything else.)

## Job progress drawer

In the streaming log, the `[embed]` and `[attach]` tags are useful — render them as small colored badges instead of plain brackets if you want polish:

```
Aria_001.jpg  [EMBED]  <- 'Vacation pics' (2026-04-12)
Aria_002.pdf  [ATTACH] <- 'Vacation pics' (2026-04-12)
```

Color the EMBED tag indigo, ATTACH tag slate. Optional polish.

## Don't change

- OAuth flows (Connect Gmail / Connect Microsoft / Add IMAP) — same as before.
- Account sidebar, base URL settings, healthz polling.
- The folder dropdown, naming prefix, output folder, after-download radio.
- The Reset counter and Run once buttons (just rewire Run once to send the new body shape).

That's it. Surgical change to one form section.

===
