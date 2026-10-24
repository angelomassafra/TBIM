#! python3
"""Assign the Informational Loads (ILDs) to cells and faces and update the spaces."""
from tbim import loadscmd
from tbim.revit import Context

loadscmd.run(Context(__revit__), clusterize=False)  # noqa: F821
