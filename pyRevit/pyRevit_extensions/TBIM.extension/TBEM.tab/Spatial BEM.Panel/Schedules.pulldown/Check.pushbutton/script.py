#! python3
"""Check the schedules named by programs and cells."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Schedules", pipeline.check_schedules)
