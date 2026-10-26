#! python3
"""Build the Topological BEM."""
from tbem import files, pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Topological BEM", lambda: pipeline.build(files.TOPOLOGICAL))
