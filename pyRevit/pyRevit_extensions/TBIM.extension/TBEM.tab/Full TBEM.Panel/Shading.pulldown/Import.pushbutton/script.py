#! python3
"""Import context shading."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Shading", pipeline.import_shades)
