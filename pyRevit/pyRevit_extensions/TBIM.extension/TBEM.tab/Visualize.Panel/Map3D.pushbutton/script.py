#! python3
"""Color the cells by a result of their zone."""
from tbem import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("3D Map", lambda: pipeline.for_level(
    "tbem_results_level", "3D Map: model", lambda level: pipeline.show_map_3d(ctx, level), simulated=True))
