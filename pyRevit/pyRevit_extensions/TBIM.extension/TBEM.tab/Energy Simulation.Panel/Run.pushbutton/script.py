#! python3
"""Run EnergyPlus on a TBEM model."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Run", lambda: pipeline.for_level(
    "tbem_run_level", "Run: model", pipeline.run))
