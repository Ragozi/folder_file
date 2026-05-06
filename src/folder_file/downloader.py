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
    msg: Message, allowed_exts: tuple[str, ...]
) -> list[tuple[str, bytes]]:
    """Walk a message and return [(original_filename, raw_bytes), ...] for attachments
    whose extension is in allowed_exts. Inline parts are skipped unless their disposition
    says attachment."""
    out: list[tuple[str, bytes]] = []
    if not msg.is_multipart() and msg.get_filename() is None:
        return out

    allow_all = not allowed_exts

    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if not filename:
            continue
        if "attachment" not in disp:
            ext_only = Path(filename).suffix.lower()
            if not (allow_all or ext_only in allowed_exts):
                continue
        ext = Path(filename).suffix.lower()
        if not (allow_all or ext in allowed_exts):
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            payload = None
        if not payload:
            continue
        out.append((filename, payload))
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
