"""Top-level CLI dispatcher for the openmock command."""

from __future__ import annotations

import sys
import argparse
from importlib.metadata import version


def main(args: list[str] | None = None) -> int:
    # pylint: disable=import-outside-toplevel
    argv = list(sys.argv[1:] if args is None else args)

    if argv == ["--version"]:
        print(f"openmock {version('openmock')}")
        return 0
    if argv in (["--help"], ["-h"]):
        parser = argparse.ArgumentParser(
            prog="openmock",
            description="Mock OpenSearch locally; the default command opens the web UI.",
        )
        parser.add_argument(
            "command",
            nargs="?",
            choices=["gui", "serve"],
            help="Tk GUI or HTTP REST server",
        )
        parser.add_argument(
            "--version", action="store_true", help="show the installed version and exit"
        )
        parser.print_help()
        return 0

    if argv and argv[0] == "gui":
        from openmock.gui import main as gui_main

        return gui_main()

    if argv and argv[0] == "serve":
        from openmock.rest_bridge import main as serve_main

        return serve_main()

    from openmock.web import main as web_main

    return web_main(argv)
