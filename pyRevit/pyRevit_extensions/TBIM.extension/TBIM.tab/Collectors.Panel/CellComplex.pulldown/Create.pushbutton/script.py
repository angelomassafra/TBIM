#! python3
"""Create the Informational Controllers (building storeys, walls, floors, roofs, spaces) from the BReps."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Informational Controllers", lambda: pipeline.controllers(ctx))
