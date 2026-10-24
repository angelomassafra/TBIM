"""Create a new Informational Load Dictionary (ILD) from an existing one."""
from pyrevit import forms, script

from tbim import ild

ilds = ild.load()
template_name = forms.SelectFromList.show(ild.occupancy_types(ilds), title="Template ILD", button_name="Select")
if not template_name:
    script.exit()
template = ild.by_occupancy_type(ilds, template_name)
name = forms.ask_for_string(title="TBIM - New ILD", prompt="Name of the new ILD (pr_OccupancyType):")
if not name:
    script.exit()
if ild.by_occupancy_type(ilds, name):
    forms.alert("An ILD named '%s' already exists." % name, title="TBIM - New ILD", exitscript=True)
new = {ild.OCCUPANCY_KEY: name}
for key in sorted(k for k in template if k != ild.OCCUPANCY_KEY):
    text = forms.ask_for_string(default=str(template[key]), title="TBIM - New ILD", prompt="%s:" % key)
    if text is None:
        script.exit()
    try:
        new[key] = ild.coerce_like(text, template[key])
    except ValueError as e:
        forms.alert(str(e), title="TBIM - New ILD", exitscript=True)
ilds.append(new)
ild.save(ilds)
forms.alert("ILD '%s' has been added to the ILD file." % name, title="TBIM - Informational Loads")
