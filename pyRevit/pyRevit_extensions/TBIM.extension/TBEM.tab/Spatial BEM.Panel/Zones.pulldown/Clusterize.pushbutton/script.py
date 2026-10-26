#! python3
"""Cluster the cells in thermal zones with the TBEM settings."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.clusterize(ctx))
