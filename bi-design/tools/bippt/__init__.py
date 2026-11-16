"""bippt – PowerPoint im Boehringer-Ingelheim-Design erzeugen, prüfen, rendern und umwandeln (Plugin bi-design)."""
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
try:
    __version__ = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
except (OSError, ValueError, KeyError):
    __version__ = "0"
