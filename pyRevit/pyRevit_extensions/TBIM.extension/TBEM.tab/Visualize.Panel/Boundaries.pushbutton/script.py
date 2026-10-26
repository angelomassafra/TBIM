#! python3
"""Color the faces by boundary condition."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Boundaries", lambda: pipeline.show_boundaries(ctx))
