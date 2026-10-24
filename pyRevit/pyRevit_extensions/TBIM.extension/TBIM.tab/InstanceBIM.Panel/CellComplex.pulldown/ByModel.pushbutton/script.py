#! python3
"""Compute the instance data derived from the model (areas, volumes, occupancy, ventilation)."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Instance BIM", lambda: pipeline.by_model(ctx))
