#! python3
"""Create the InstanceBIM: move the TBIM apertures like the doors and windows moved in Revit."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Instance BIM", lambda: pipeline.move_apertures(ctx))
