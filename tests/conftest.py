from __future__ import annotations

from email.message import EmailMessage

import pytest


@pytest.fixture
def sample_email() -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Vacation pics"
    msg["From"] = "alice@example.com"
    msg["To"] = "bob@example.com"
    msg["Date"] = "Mon, 12 Apr 2026 10:00:00 -0400"
    msg.set_content("Some pics + a doc.")
    msg.add_attachment(
        b"\xff\xd8\xff\xe0fake-jpeg-bytes",
        maintype="image",
        subtype="jpeg",
        filename="beach.jpg",
    )
    msg.add_attachment(
        b"\x89PNG\r\n\x1a\nfake-png-bytes",
        maintype="image",
        subtype="png",
        filename="sunset.PNG",
    )
    msg.add_attachment(
        b"%PDF-1.4 fake pdf bytes",
        maintype="application",
        subtype="pdf",
        filename="receipt.pdf",
    )
    msg.add_attachment(
        b"hello world",
        maintype="text",
        subtype="plain",
        filename="notes.txt",
    )
    return msg


@pytest.fixture
def email_no_attachments() -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Just text"
    msg["From"] = "alice@example.com"
    msg["Date"] = "Tue, 13 Apr 2026 09:00:00 -0400"
    msg.set_content("Body only, no attachments.")
    return msg


@pytest.fixture
def email_with_embedded_image() -> EmailMessage:
    """HTML email with a cid:-referenced inline image and no explicit filename
    on the image part — what "paste pic into Outlook" produces."""
    msg = EmailMessage()
    msg["Subject"] = "Look at this!"
    msg["From"] = "alice@example.com"
    msg["Date"] = "Wed, 14 Apr 2026 10:00:00 -0400"
    msg.set_content("Plain-text fallback.")
    msg.add_alternative(
        '<html><body><p>Pic:</p><img src="cid:img1@x"></body></html>',
        subtype="html",
    )
    html_part = msg.get_payload()[1]
    html_part.add_related(
        b"\xff\xd8\xff\xe0fake-jpeg-bytes",
        maintype="image",
        subtype="jpeg",
        cid="<img1@x>",
    )
    return msg


@pytest.fixture
def email_mixed_sources() -> EmailMessage:
    """An email with BOTH a cid:-embedded image AND a regular file attachment.
    Mirrors the realistic 'pic pasted in body, plus a PDF attached' case."""
    msg = EmailMessage()
    msg["Subject"] = "Quarterly report + photo"
    msg["From"] = "alice@example.com"
    msg["Date"] = "Thu, 15 Apr 2026 09:00:00 -0400"
    msg.set_content("See pic below and attached PDF.")
    msg.add_alternative(
        '<html><body>Pic: <img src="cid:abc"><br>See attached.</body></html>',
        subtype="html",
    )
    html_part = msg.get_payload()[1]
    html_part.add_related(
        b"\xff\xd8\xff\xe0embedded-jpeg-bytes",
        maintype="image",
        subtype="jpeg",
        cid="<abc>",
    )
    msg.add_attachment(
        b"%PDF-1.4 attached pdf bytes",
        maintype="application",
        subtype="pdf",
        filename="report.pdf",
    )
    return msg
