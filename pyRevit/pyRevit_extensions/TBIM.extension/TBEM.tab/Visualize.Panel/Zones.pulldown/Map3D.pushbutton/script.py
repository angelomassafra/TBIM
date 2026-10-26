#! python3
"""Color the cells by thermal zone."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.show_zones(ctx))
