"""Tray-app launcher: starts the FastAPI server in a background thread,
opens the bundled UI in the default browser, and parks a system-tray icon
the user can use to re-open the UI or quit. This is the entry point used
by the packaged Windows / Mac builds — no terminal required."""

from __future__ import annotations

import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from folder_file.api import create_app
from folder_file.config import DEFAULT_API_HOST, DEFAULT_API_PORT


def _create_icon_image():
    """Build a simple icon at runtime so we don't ship a separate file."""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Indigo rounded square with a folder glyph
    draw.rounded_rectangle((4, 4, size - 4, size - 4), radius=10, fill=(79, 70, 229))
    # Folder tab
    draw.rectangle((14, 18, 32, 24), fill=(255, 255, 255))
    # Folder body
    draw.rounded_rectangle((14, 22, 50, 46), radius=3, fill=(255, 255, 255))
    return img


def _wait_for_server(url: str, timeout_sec: float = 10.0) -> bool:
    """Poll /healthz until it answers or we give up."""
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_sec
    health = url.rstrip("/") + "/healthz"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=1) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.2)
    return False


def main() -> None:
    host = DEFAULT_API_HOST
    port = DEFAULT_API_PORT
    url = f"http://{host}:{port}/"

    app = create_app()

    # Run uvicorn in a background thread so the tray icon can own the main loop.
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    server_thread.start()

    # Wait for the server to actually accept connections before opening the browser
    # — otherwise the user sees a "site can't be reached" flash.
    if _wait_for_server(url):
        webbrowser.open(url)
    else:
        # Server didn't come up; bail with a console message (visible if launched
        # from terminal, ignored if launched headlessly via the .exe).
        print(
            "folder_file: server failed to start within 10 seconds. "
            "Check that port 8765 isn't already in use.",
            file=sys.stderr,
        )
        return

    # Tray icon — imported lazily so a missing display backend doesn't crash
    # the whole entry point on headless systems / CI.
    try:
        import pystray
    except Exception as e:  # noqa: BLE001
        print(f"folder_file: tray icon unavailable ({e}); server still running at {url}", file=sys.stderr)
        # Keep the server thread alive as long as the user wants
        try:
            server_thread.join()
        except KeyboardInterrupt:
            server.should_exit = True
        return

    def on_open(_icon, _item):
        webbrowser.open(url)

    def on_quit(icon, _item):
        icon.stop()

    icon = pystray.Icon(
        "folder_file",
        _create_icon_image(),
        "folder_file",
        menu=pystray.Menu(
            pystray.MenuItem("Open folder_file", on_open, default=True),
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    try:
        icon.run()
    finally:
        server.should_exit = True
        server_thread.join(timeout=3)


if __name__ == "__main__":
    main()
