#! python3
"""Back to the thermal zones of the TBIM."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.reset_zones(ctx))
