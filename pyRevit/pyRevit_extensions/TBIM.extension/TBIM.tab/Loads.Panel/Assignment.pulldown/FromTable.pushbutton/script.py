#! python3
"""Assign occupancy types and space names from the table of rooms of the project (tbim_Rooms.json)."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Assignment", lambda: pipeline.assign_from_table(ctx))
