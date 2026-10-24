"""Select the BRep files (one per building block) of the 3D model."""
import os

from pyrevit import forms, script

from tbim import paths, projects
from tbim.jsonio import write_json

folder = projects.active_project()
brep_paths = forms.pick_file(file_ext="brep", multi_file=True, unc_paths=False,
                             init_dir=os.path.join(folder, projects.MODEL_FOLDER) if folder else None)
if not brep_paths:
    script.exit()
# paths inside the project folder are stored relative to it: the project can be moved
path = write_json(paths.data_file(paths.BREP_FILEPATHS), [projects.relative(p) for p in brep_paths])
forms.alert("%d BRep file paths have been set:\n\n%s" % (len(brep_paths), "\n".join(brep_paths)), title="TBIM - Import")
