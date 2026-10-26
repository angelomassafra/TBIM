#! python3
"""Set the building airtightness."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Infiltration", pipeline.set_infiltration)
