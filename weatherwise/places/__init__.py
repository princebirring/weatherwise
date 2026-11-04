"""Location-agnostic places: a point in, everything derived.

No village tables. Any coordinate is resolved on demand to its admin area, forecast
grid cell, terrain and river exposure, and each result is cached by grid cell.
"""
