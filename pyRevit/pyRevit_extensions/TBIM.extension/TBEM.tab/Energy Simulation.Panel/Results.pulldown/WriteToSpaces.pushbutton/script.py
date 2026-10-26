#! python3
"""Write the results to the Revit spaces."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Results", lambda: pipeline.for_level(
    "tbem_results_level", "Results: model", lambda level: pipeline.write_results(ctx, level), simulated=True))
