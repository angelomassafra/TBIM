"""Assign an occupancy type to all the spaces of a building storey."""
from pyrevit import forms, script

from tbim import assignment, revit

doc = revit.Context(__revit__).doc  # noqa: F821
storey = forms.SelectFromList.show([lv.Name for lv in revit.levels(doc)], title="Building storey", button_name="Select")
if not storey:
    script.exit()
occupancy = assignment.pick_occupancy_type("Occupancy type for the spaces of %s" % storey)
assignment.assign(doc, [s for s in revit.spaces(doc) if s.Level is not None and s.Level.Name == storey], occupancy)
