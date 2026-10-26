#! python3
"""Fill the spaces by thermal zone in floor plans."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.show_zones_2d(ctx))
