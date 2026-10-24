#! python3
"""Place windows and doors by rules (tbim_TopologicalBIM_Rules.json) on the TBIM and in the Revit model."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("TopologicalBIM", lambda: pipeline.topological_bim(ctx))
