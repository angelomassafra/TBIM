#! python3
"""Write the InstanceBIM data to Revit spaces, walls, floors, roofs, windows and doors (matched by UID)."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Instance BIM", lambda: pipeline.update_revit(ctx))
