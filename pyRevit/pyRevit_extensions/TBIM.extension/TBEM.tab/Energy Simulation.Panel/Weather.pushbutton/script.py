#! python3
"""Pick the weather file."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Weather", pipeline.set_weather)
