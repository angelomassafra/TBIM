#! python3
"""Show the dual graph of the cells: cells sharing a wall or a slab."""
from tbim import revit, scene
from tbim import visualize as viz

viz.show_graph(revit.Context(__revit__), scene.ADJACENCY, "Dual graph")  # noqa: F821
