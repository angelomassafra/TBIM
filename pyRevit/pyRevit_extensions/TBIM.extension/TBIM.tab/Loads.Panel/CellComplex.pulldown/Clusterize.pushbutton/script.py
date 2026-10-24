#! python3
"""Assign the Informational Loads (ILDs) and cluster the cells in thermal zones."""
from tbim import loadscmd
from tbim.revit import Context

loadscmd.run(Context(__revit__), clusterize=True)  # noqa: F821
