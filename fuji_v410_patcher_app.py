#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from fuji_v410_patcher import main as cli_main

        return cli_main(sys.argv[1:])

    from fuji_v410_patcher import attach_parent_console, print_usage

    if attach_parent_console():
        print_usage()
        sys.stdout.flush()
        return 0

    from fuji_v410_patcher_gui import FujiPatcherApp

    app = FujiPatcherApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
