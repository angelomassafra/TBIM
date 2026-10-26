#! python3
"""Selected faces: boundary of the topology."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Boundaries", lambda: pipeline.set_boundary(ctx, None))
