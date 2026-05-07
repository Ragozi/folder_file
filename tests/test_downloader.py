from __future__ import annotations

from pathlib import Path

from folder_file.downloader import (
    extract_attachments,
    next_filename,
    normalize_extensions,
    save,
)


def _names(items):
    return sorted(n for n, _, _ in items)


def _by_source(items):
    out = {"embedded": [], "attachment": []}
    for n, _, src in items:
        out[src].append(n)
    for k in out:
        out[k].sort()
    return out


def test_normalize_extensions_dedupes_and_lowers():
    assert normalize_extensions(["JPG", ".jpg", "pdf", "PDF"]) == (".jpg", ".pdf")


def test_normalize_extensions_handles_blanks():
    assert normalize_extensions([" ", "", ".PNG"]) == (".png",)


def test_extract_attachments_filter_by_attachment_exts(sample_email):
    """sample_email has only regular attachments; filter applies via attachment_exts."""
    out = extract_attachments(
        sample_email,
        attachment_exts=normalize_extensions([".jpg", ".png"]),
    )
    assert _names(out) == ["beach.jpg", "sunset.PNG"]
    assert all(s == "attachment" for _, _, s in out)


def test_extract_attachments_filter_pdf_only(sample_email):
    out = extract_attachments(sample_email, attachment_exts=(".pdf",))
    assert _names(out) == ["receipt.pdf"]


def test_extract_attachments_empty_filter_takes_all_for_that_source(sample_email):
    # No filters at all = take everything.
    out = extract_attachments(sample_email)
    assert _names(out) == ["beach.jpg", "notes.txt", "receipt.pdf", "sunset.PNG"]


def test_extract_attachments_no_attachments(email_no_attachments):
    assert extract_attachments(email_no_attachments, attachment_exts=(".pdf",)) == []


def test_extract_attachments_picks_up_embedded_inline_image(email_with_embedded_image):
    out = extract_attachments(email_with_embedded_image, embedded_exts=(".jpg",))
    assert len(out) == 1
    name, data, source = out[0]
    assert name.endswith(".jpg")
    assert b"embedded" in data or b"jpeg" in data
    assert source == "embedded"


def test_extract_attachments_embedded_image_respects_embedded_filter(
    email_with_embedded_image,
):
    # Only .pdf allowed for embedded -> the embedded jpg is excluded.
    assert extract_attachments(email_with_embedded_image, embedded_exts=(".pdf",)) == []


def test_extract_mixed_email_takes_both_by_default(email_mixed_sources):
    out = extract_attachments(email_mixed_sources)
    by = _by_source(out)
    assert any(n.endswith(".jpg") for n in by["embedded"])
    assert by["attachment"] == ["report.pdf"]


def test_extract_mixed_email_drops_embedded(email_mixed_sources):
    out = extract_attachments(email_mixed_sources, include_embedded=False)
    by = _by_source(out)
    assert by["embedded"] == []
    assert by["attachment"] == ["report.pdf"]


def test_extract_mixed_email_drops_attachments(email_mixed_sources):
    out = extract_attachments(email_mixed_sources, include_attachments=False)
    by = _by_source(out)
    assert by["attachment"] == []
    assert len(by["embedded"]) == 1


def test_extract_mixed_email_per_source_extension_filter(email_mixed_sources):
    """Embedded images: jpg only. Attachments: pdf only.
    Mixed message should yield one of each."""
    out = extract_attachments(
        email_mixed_sources,
        embedded_exts=(".jpg",),
        attachment_exts=(".pdf",),
    )
    by = _by_source(out)
    assert len(by["embedded"]) == 1
    assert by["attachment"] == ["report.pdf"]


def test_extract_mixed_email_pdf_embedded_jpg_attachment_filter(email_mixed_sources):
    """Embedded must be .pdf (none qualifies); attachments must be .jpg (none qualifies)."""
    out = extract_attachments(
        email_mixed_sources,
        embedded_exts=(".pdf",),
        attachment_exts=(".jpg",),
    )
    assert out == []


def test_next_filename_zero_pads_three_digits():
    assert next_filename("Aria", 1, "beach.JPG") == "Aria_001.jpg"
    assert next_filename("Aria", 42, "x.pdf") == "Aria_042.pdf"
    assert next_filename("Aria", 999, "x.pdf") == "Aria_999.pdf"


def test_next_filename_grows_past_999():
    assert next_filename("Aria", 1000, "x.pdf") == "Aria_1000.pdf"
    assert next_filename("Aria", 12345, "x.pdf") == "Aria_12345.pdf"


def test_next_filename_lowercases_extension():
    assert next_filename("Test", 7, "PHOTO.JPEG") == "Test_007.jpeg"


def test_save_writes_file_and_returns_path(tmp_path: Path):
    out = save(tmp_path, "thing_001.txt", b"hello")
    assert out == tmp_path / "thing_001.txt"
    assert out.read_bytes() == b"hello"


def test_save_handles_collision(tmp_path: Path):
    save(tmp_path, "thing_001.txt", b"first")
    second = save(tmp_path, "thing_001.txt", b"second")
    assert second.name == "thing_001__dup1.txt"
    assert second.read_bytes() == b"second"
