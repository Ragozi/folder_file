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
