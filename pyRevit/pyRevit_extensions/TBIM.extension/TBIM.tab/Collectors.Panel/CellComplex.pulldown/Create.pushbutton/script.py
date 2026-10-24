#! python3
"""Create the Informational Controllers (building storeys, walls, spaces) from the BReps."""
from tbim import collectors, paths, projects, topo
from tbim.jsonio import read_json
from tbim.revit import Context, alert

ctx = Context(__revit__)  # noqa: F821
brep_paths = [projects.resolve(p) for p in read_json(paths.data_file(paths.BREP_FILEPATHS), default=[])]
if not brep_paths:
    alert("Informational Controllers", "No BRep selected: use 3D Model > Import first.")
else:
    cc, report = collectors.run(ctx, brep_paths)
    path = topo.save_cellcomplex(cc, paths.data_file(paths.CC_CONTROLLERS))
    alert("Informational Controllers", "\n".join(report) + "\n\nExported to:\n%s" % path)
