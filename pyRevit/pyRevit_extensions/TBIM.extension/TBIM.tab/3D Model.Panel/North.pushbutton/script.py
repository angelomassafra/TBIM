"""Set the angle of the Project North (degrees, counterclockwise)."""
from pyrevit import forms, script

from tbim import paths
from tbim.jsonio import read_json, write_json

path = paths.data_file(paths.NORTH_ANGLE)
current = read_json(path, default=0)
text = forms.ask_for_string(default=str(current), title="TBIM - North Angle",
                            prompt="Angle of the Project North vector (degrees). Positive angles are counterclockwise.")
if text is None:
    script.exit()
try:
    angle = float(text.replace(",", "."))
except ValueError:
    forms.alert("'%s' is not a number." % text, title="TBIM - North Angle", exitscript=True)
write_json(path, angle)
forms.alert("Project North Angle has been set to %s degrees." % angle, title="TBIM - North Angle")
