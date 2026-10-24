#! python3
"""Assign the Informational Loads (ILDs) and cluster the cells in thermal zones."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Informational Loads", lambda: pipeline.loads(ctx, clusterize=True))
