#! python3
"""Check the constructions of the Full TBEM."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Constructions", pipeline.check_constructions)
