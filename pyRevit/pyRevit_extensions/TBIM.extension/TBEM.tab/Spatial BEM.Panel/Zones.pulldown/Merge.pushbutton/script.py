#! python3
"""Merge the selected spaces in one thermal zone."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Thermal zones", lambda: pipeline.merge_selected(ctx))
