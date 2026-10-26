#! python3
"""Check the inputs of the TBEM of the project."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Check model", pipeline.check)
