#! python3
"""Check the BEM programs of the occupancy types."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Programs", pipeline.check_programs)
