#! python3
"""Show the passage graph of the cells: doors, stairs and entrances."""
from tbim import revit, scene
from tbim import visualize as viz

viz.show_graph(revit.Context(__revit__), scene.PASSAGE, "Passage graph")  # noqa: F821
