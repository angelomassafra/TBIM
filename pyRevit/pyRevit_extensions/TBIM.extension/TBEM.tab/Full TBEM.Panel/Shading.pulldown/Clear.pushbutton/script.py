#! python3
"""Remove the context shading."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Shading", pipeline.clear_shades)
