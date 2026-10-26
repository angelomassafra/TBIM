#! python3
"""Show the active project and the TBEM progress."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Info", lambda: pipeline.info(ctx))
