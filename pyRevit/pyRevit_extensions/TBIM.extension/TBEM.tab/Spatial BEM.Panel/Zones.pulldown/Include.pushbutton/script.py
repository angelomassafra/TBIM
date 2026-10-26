#! python3
"""Model again the selected spaces."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.include_selected(ctx))
