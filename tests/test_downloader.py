from __future__ import annotations

from pathlib import Path

from folder_file.downloader import (
    extract_attachments,
    next_filename,
    normalize_extensions,
    save,
)


def test_normalize_extensions_dedupes_and_lowers():
    assert normalize_extensions(["JPG", ".jpg", "pdf", "PDF"]) == (".jpg", ".pdf")


def test_normalize_extensions_handles_blanks():
    assert normalize_extensions([" ", "", ".PNG"]) == (".png",)


def test_extract_attachments_filters_by_extension(sample_email):
    out = extract_attachments(sample_email, normalize_extensions([".jpg", ".png"]))
    names = sorted(n for n, _ in out)
    assert names == ["beach.jpg", "sunset.PNG"]


def test_extract_attachments_filter_pdf_only(sample_email):
    out = extract_attachments(sample_email, (".pdf",))
    names = [n for n, _ in out]
    assert names == ["receipt.pdf"]


def test_extract_attachments_empty_filter_takes_all(sample_email):
    out = extract_attachments(sample_email, ())
    names = sorted(n for n, _ in out)
    assert names == ["beach.jpg", "notes.txt", "receipt.pdf", "sunset.PNG"]


def test_extract_attachments_skips_text_when_not_allowed(sample_email):
    out = extract_attachments(sample_email, (".pdf", ".jpg"))
    names = sorted(n for n, _ in out)
    assert names == ["beach.jpg", "receipt.pdf"]


def test_extract_attachments_no_attachments(email_no_attachments):
    assert extract_attachments(email_no_attachments, (".pdf",)) == []


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
