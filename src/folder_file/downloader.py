from __future__ import annotations

from email.message import Message
from pathlib import Path


def _normalize_ext(ext: str) -> str:
    ext = ext.strip().lower()
    if not ext:
        return ""
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def normalize_extensions(exts: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for e in exts:
        n = _normalize_ext(e)
        if n and n not in seen:
            seen.append(n)
    return tuple(seen)


def extract_attachments(
    msg: Message,
    *,
    include_embedded: bool = True,
    embedded_exts: tuple[str, ...] = (),
    include_attachments: bool = True,
    attachment_exts: tuple[str, ...] = (),
) -> list[tuple[str, bytes, str]]:
    """Walk a message and return [(filename, raw_bytes, source), ...]
    where source is "embedded" or "attachment".

    Classification:
    - "embedded": part has Content-ID OR Content-Disposition contains "inline".
      These are the cid:-referenced images Outlook produces when you paste a
      picture into a message body.
    - "attachment": everything else with a filename — files added via
      "Attach file" / drag-drop into the attachments tray.

    Filtering (applied per-source):
    - If include_<source> is False, skip parts of that source entirely.
    - If <source>_exts is non-empty, the part's extension (lowercased) must
      be in the list. Empty list means "any extension".

    HTML <img src="https://..."> URLs are NOT followed; those bytes don't
    live in the email and would require a separate fetch."""
    out: list[tuple[str, bytes, str]] = []

    for part in msg.walk():
        if part.is_multipart():
            continue

        disp = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        maintype = part.get_content_maintype()
        subtype = (part.get_content_subtype() or "").lower()
        cid = part.get("Content-ID")

        is_embedded = bool(cid) or "inline" in disp
        source = "embedded" if is_embedded else "attachment"

        if source == "embedded" and not include_embedded:
            continue
        if source == "attachment" and not include_attachments:
            continue

        if not filename:
            # No explicit filename. Only keep this part if it's clearly an
            # embedded image (image MIME type AND already classified embedded).
            # Otherwise it's likely the message body, a signature, etc.
            if not (is_embedded and maintype == "image"):
                continue
            ext_synth = "jpg" if subtype == "jpeg" else (subtype or "bin")
            filename = f"embedded.{ext_synth}"

        ext = Path(filename).suffix.lower()
        allowed = embedded_exts if source == "embedded" else attachment_exts
        if allowed and ext not in allowed:
            continue

        try:
            payload = part.get_payload(decode=True)
        except Exception:
            payload = None
        if not payload:
            continue
        out.append((filename, payload, source))
    return out


def next_filename(prefix: str, counter: int, original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    width = 3 if counter < 1000 else len(str(counter))
    return f"{prefix}_{counter:0{width}d}{ext}"


def save(directory: Path, filename: str, data: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if target.exists():
        stem, suffix = target.stem, target.suffix
        n = 1
        while True:
            alt = directory / f"{stem}__dup{n}{suffix}"
            if not alt.exists():
                target = alt
                break
            n += 1
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(target)
    return target
