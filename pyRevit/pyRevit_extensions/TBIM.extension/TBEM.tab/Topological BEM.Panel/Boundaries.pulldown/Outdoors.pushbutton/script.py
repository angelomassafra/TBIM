#! python3
"""Selected faces: outdoors."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Boundaries", lambda: pipeline.set_boundary(ctx, "Outdoors"))
