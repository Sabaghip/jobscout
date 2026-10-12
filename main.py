from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) == 1 or sys.argv[1] == "gui":
        from jobscout.gui import main as gui_main

        gui_main()
    else:
        from jobscout.cli import main as cli_main

        cli_main()


if __name__ == "__main__":
    main()
