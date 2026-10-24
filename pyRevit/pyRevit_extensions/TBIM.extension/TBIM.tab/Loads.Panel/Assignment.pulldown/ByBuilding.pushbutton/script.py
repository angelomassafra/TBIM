"""Assign an occupancy type to all the spaces of the building."""
from tbim import assignment, revit

doc = revit.Context(__revit__).doc  # noqa: F821
occupancy = assignment.pick_occupancy_type("Occupancy type for all the spaces")
assignment.assign(doc, revit.spaces(doc), occupancy)
