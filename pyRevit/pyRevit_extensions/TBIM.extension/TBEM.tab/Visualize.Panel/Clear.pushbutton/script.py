#! python3
"""Delete the TBEM visualizations."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Visualize", lambda: pipeline.clear_visualizations(ctx))
