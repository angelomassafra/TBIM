#! python3
"""Summarise the results of a simulation."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Results", lambda: pipeline.for_level(
    "tbem_results_level", "Results: model", pipeline.results, simulated=True))
