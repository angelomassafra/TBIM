#! python3
"""Chart the results of a simulation."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Charts", lambda: pipeline.for_level(
    "tbem_results_level", "Charts: model", pipeline.show_charts, simulated=True))
