#! python3
"""Add the instance data defined by occupancy type to the cells."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Instance BIM", lambda: pipeline.by_occupancy_type(ctx))
