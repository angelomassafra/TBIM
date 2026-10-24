"""Show the properties of an Informational Load Dictionary (ILD)."""
from pyrevit import forms, script

from tbim import ild

ilds = ild.load()
name = forms.SelectFromList.show(ild.occupancy_types(ilds), title="ILD to read", button_name="Read")
if not name:
    script.exit()
dictionary = ild.by_occupancy_type(ilds, name)
print("Informational Load Dictionary: %s" % name)
for key in sorted(dictionary):
    print("  %s: %s" % (key, dictionary[key]))
