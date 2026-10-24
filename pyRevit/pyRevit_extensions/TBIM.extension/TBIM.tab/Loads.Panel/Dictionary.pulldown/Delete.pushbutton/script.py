"""Delete an Informational Load Dictionary (ILD)."""
from pyrevit import forms, script

from tbim import ild

ilds = ild.load()
names = [n for n in ild.occupancy_types(ilds) if n != ild.DEFAULT_OCCUPANCY]
name = forms.SelectFromList.show(names, title="ILD to delete", button_name="Delete")
if not name:
    script.exit()
ild.save([d for d in ilds if d[ild.OCCUPANCY_KEY] != name])
forms.alert("ILD '%s' has been deleted from the ILD file." % name, title="TBIM - Informational Loads")
