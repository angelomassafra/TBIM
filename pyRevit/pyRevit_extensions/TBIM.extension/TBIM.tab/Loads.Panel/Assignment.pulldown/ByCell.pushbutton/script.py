"""Assign an occupancy type to the selected spaces (cells)."""
from Autodesk.Revit.DB import BuiltInCategory
from pyrevit import revit as pyrevit_revit
from pyrevit import script

from tbim import assignment, revit

doc = revit.Context(__revit__).doc  # noqa: F821
picked = pyrevit_revit.pick_elements_by_category(BuiltInCategory.OST_MEPSpaces, message="Select spaces, then Finish")
if not picked:
    script.exit()
occupancy = assignment.pick_occupancy_type("Occupancy type for %d spaces" % len(picked))
assignment.assign(doc, picked, occupancy)
