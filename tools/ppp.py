"""Command line of ppp. Call: python -I <plugin>/tools/ppp.py <command> [options]

Runs with the Python standard library only (3.10 or later). `-I` keeps the script directory off sys.path,
so the package next to this file is added explicitly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ppplib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
