#! python3
"""Leave the selected spaces out of the energy model."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.exclude_selected(ctx))
