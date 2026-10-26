#! python3
"""Import schedules into the library."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Schedules", pipeline.import_schedules)
