#! python3
"""Open the TBEM folder."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Folder", pipeline.open_folder)
