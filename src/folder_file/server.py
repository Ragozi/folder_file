from __future__ import annotations

import argparse
import webbrowser

import uvicorn

from folder_file.api import create_app
from folder_file.config import DEFAULT_API_HOST, DEFAULT_API_PORT


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="folder_file.server",
        description="Run the folder_file local HTTP API.",
    )
    parser.add_argument("--host", default=DEFAULT_API_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT)
    parser.add_argument(
        "--open-ui",
        action="store_true",
        help="Open the configured Lovable URL in your browser at startup.",
    )
    parser.add_argument("--ui-url", default=None, help="URL to open with --open-ui")
    args = parser.parse_args()

    app = create_app()

    print(f"folder_file API listening on http://{args.host}:{args.port}")
    print("Endpoints: /healthz, /accounts, /auth/gmail/start, /auth/microsoft/start,")
    print("           /accounts/{id}/folders, /run, /jobs/{id}")
    print()

    if args.open_ui and args.ui_url:
        try:
            webbrowser.open(args.ui_url)
        except Exception:
            pass

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
