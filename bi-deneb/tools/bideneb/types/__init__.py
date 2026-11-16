"""The catalogue of visual types. Importing the modules registers their types."""
from .common import TYPES  # noqa: F401
from . import bars, trend, compare, matrix, dist, timeline, kpi  # noqa: F401,E402
