#! python3
"""Export a TBEM model to EnergyPlus."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("IDF", lambda: pipeline.for_level(
    "tbem_idf_level", "IDF: model", pipeline.export_idf))
