#! python3
"""Assign the Informational Loads (ILDs) to the cells and faces."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Informational Loads", lambda: pipeline.loads(ctx, clusterize=False))
