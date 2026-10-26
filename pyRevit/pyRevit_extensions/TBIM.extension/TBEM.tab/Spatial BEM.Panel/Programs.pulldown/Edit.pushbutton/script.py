#! python3
"""Open the BEM programs."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Programs", pipeline.edit_programs)
