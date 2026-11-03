#!/usr/bin/env python3
"""NET+ LAB launcher.  Run:  python netplus_lab.py   (Python 3.10+, standard library only)."""

import sys

if sys.version_info < (3, 10):
    sys.exit("NET+ LAB needs Python 3.10 or newer.")

try:
    import tkinter  # noqa: F401
except ImportError:
    sys.exit("Tkinter is missing. Linux: install python3-tk (Debian/Ubuntu) or python3-tkinter (Fedora). "
             "Windows/macOS: reinstall Python from python.org with the tcl/tk option enabled.")

from netplus.app import main

if __name__ == "__main__":
    main()
