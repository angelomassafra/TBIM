"""Assignment of occupancy types to spaces (IronPython: uses pyrevit.forms)."""
from pyrevit import forms, script

from tbim import ild, revit


def pick_occupancy_type(prompt):
    name = forms.SelectFromList.show(ild.occupancy_types(ild.load()), title=prompt, button_name="Assign")
    if not name:
        script.exit()
    return name


def assign(doc, spaces, occupancy_type):
    """Set pr_OccupancyType on ``spaces`` and export the assignments of all the spaces."""
    with revit.transaction(doc, "Assign occupancy type"):
        for space in spaces:
            revit.set_by_name(space, "pr_OccupancyType", occupancy_type)
    path = ild.save_assignments(revit.occupancy_assignments(doc))
    forms.alert("'%s' assigned to %d spaces.\n\nAssignments exported to:\n%s" % (occupancy_type, len(spaces), path),
                title="TBIM - Assignment")
