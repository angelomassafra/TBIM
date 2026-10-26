#! python3
"""Fill the spaces by a result of their zone in floor plans."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("2D Map", lambda: pipeline.for_level(
    "tbem_results_level", "2D Map: model", lambda level: pipeline.show_map_2d(ctx, level), simulated=True))
