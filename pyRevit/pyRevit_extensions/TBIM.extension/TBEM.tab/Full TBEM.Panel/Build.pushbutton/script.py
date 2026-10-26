#! python3
"""Build the Full TBEM."""
from tbem import files, pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Full TBEM", lambda: pipeline.build(files.FULL))
