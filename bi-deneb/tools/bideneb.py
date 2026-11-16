#!/usr/bin/env python3
"""bideneb: build, check and improve Deneb visuals for Power BI in a brand design.

  macOS:   python3 "<plugin>/tools/bideneb.py" <command>
  Windows: python "<plugin>\\tools\\bideneb.py" <command>     (without -I: it hides packages installed with pip --user)

`bideneb env` names the call with full paths; `bideneb --help` lists the commands."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bideneb.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
