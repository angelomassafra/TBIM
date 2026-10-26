#! python3
"""Build the Spatial BEM."""
from tbem import files, pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Spatial BEM", lambda: pipeline.build(files.SPATIAL))
