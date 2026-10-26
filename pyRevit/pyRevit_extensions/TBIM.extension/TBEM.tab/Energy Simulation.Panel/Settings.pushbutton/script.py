#! python3
"""Open the TBEM settings."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Settings", pipeline.edit_settings)
