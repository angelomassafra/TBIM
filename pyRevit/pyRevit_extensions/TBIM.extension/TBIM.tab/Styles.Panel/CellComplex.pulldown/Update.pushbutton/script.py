#! python3
"""Apply the Informational Rule Sets (IRSs) to the faces and give the Revit elements their layered types."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Informational Styles", lambda: pipeline.styles(ctx))
