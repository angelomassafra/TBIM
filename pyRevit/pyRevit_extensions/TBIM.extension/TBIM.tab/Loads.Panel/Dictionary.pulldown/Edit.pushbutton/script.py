"""Edit a property of an Informational Load Dictionary (ILD)."""
from pyrevit import forms, script

from tbim import ild

ilds = ild.load()
name = forms.SelectFromList.show(ild.occupancy_types(ilds), title="ILD to edit", button_name="Select")
if not name:
    script.exit()
dictionary = ild.by_occupancy_type(ilds, name)
key = forms.SelectFromList.show(sorted(k for k in dictionary if k != ild.OCCUPANCY_KEY),
                                title="Property to edit", button_name="Select")
if not key:
    script.exit()
text = forms.ask_for_string(default=str(dictionary[key]), title="TBIM - Edit ILD", prompt="%s:" % key)
if text is None:
    script.exit()
try:
    dictionary[key] = ild.coerce_like(text, dictionary[key])
except ValueError as e:
    forms.alert(str(e), title="TBIM - Edit ILD", exitscript=True)
ild.save(ilds)
forms.alert("ILD '%s' has been modified: %s = %s" % (name, key, dictionary[key]), title="TBIM - Informational Loads")
