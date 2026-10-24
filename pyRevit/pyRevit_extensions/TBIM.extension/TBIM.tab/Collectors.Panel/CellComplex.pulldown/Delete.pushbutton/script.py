"""Delete the Informational Controllers (zones, spaces, walls, floors, roofs, levels)."""
from pyrevit import forms, script

from tbim import paths
from tbim.revit import Context, alert, delete_controllers

if paths.read_settings().get("dialogs", True) and not forms.alert(
        "Delete ALL zones, spaces, walls, floors, roofs and levels of the model?",
        title="TBIM - Delete", yes=True, no=True):
    script.exit()
counts = delete_controllers(Context(__revit__).doc)  # noqa: F821
alert("Delete", "Informational Controllers have been deleted:\n\n"
      + "\n".join("%s: %d" % item for item in sorted(counts.items())))
