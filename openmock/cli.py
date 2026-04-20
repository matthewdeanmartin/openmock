"""Top-level CLI dispatcher for the openmock command."""

from __future__ import annotations

import sys


def main(args: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if args is None else args)

    if argv and argv[0] == "gui":
        from openmock.gui import main as gui_main

        return gui_main()

    from openmock.web import main as web_main

    return web_main(argv)
