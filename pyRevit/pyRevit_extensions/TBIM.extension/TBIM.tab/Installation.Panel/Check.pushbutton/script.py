#! python3
"""Check the TBIM installation: Python engine, libraries, Topologic kernel and data folder.

Also reloads the TBIM library and topologicpy (pure Python): the CPython engine of pyRevit keeps imported
modules in memory, so run Check after updating TBIM or topologicpy (pythonocc needs a Revit restart).
"""
import os
import sys

_RELOADED = ("tbim", "tbem", "topologicpy")
for _name in [m for m in sys.modules if m in _RELOADED or m.startswith(tuple(p + "." for p in _RELOADED))]:
    del sys.modules[_name]

import tbim  # noqa: E402
from tbim import __version__, paths  # noqa: E402
from tbim.revit import alert  # noqa: E402

lines = ["TBIM %s" % __version__, "Python %s" % sys.version.split()[0],
         "TBIM folder: %s" % paths.tbim_root(),
         "Data folder: %s (%s)" % (paths.data_dir(), "ok" if os.path.isdir(paths.data_dir()) else "MISSING")]
ok = True
for module in ("numpy", "scipy", "scipy.spatial", "topologicpy"):
    try:
        mod = __import__(module)
        lines.append("%s %s" % (module, getattr(mod, "__version__", "")))
    except Exception:
        import traceback
        ok = False
        lines.append("%s NOT AVAILABLE:\n%s" % (module, traceback.format_exc()))
try:  # geometry kernel: pythonocc-core (conda environment), else topologic_core
    import OCC
    lines.append("pythonocc-core %s (%s)" % (OCC.VERSION, tbim.occ_env()))
except Exception as e:
    lines.append("pythonocc-core NOT AVAILABLE (%s): create the environment of environment.yml" % e)
if ok:
    backend = tbim.topologic_backend()
    if backend is None:
        ok = False
        lines.append("Topologic backend: NONE (%s=%s)" % (tbim.BACKEND_ENV_VAR, os.environ.get(tbim.BACKEND_ENV_VAR)))
    else:
        from topologicpy.Vertex import Vertex
        ok = Vertex.ByCoordinates(0, 0, 0) is not None
        lines.append("Topologic backend: %s" % backend)
        lines.append("Topologic kernel: %s" % ("ok" if ok else "NOT WORKING"))
try:  # TBEM tab (optional): Honeybee and EnergyPlus
    from importlib.metadata import version

    from tbem import settings as tbem_settings
    folder = tbem_settings.energyplus_folder(tbem_settings.DEFAULTS)
    lines.append("TBEM: honeybee-energy %s, EnergyPlus %s" % (
        version("honeybee-energy"), folder or "NOT FOUND (install EnergyPlus 24.2)"))
except Exception as e:
    lines.append("TBEM: honeybee-energy NOT AVAILABLE (%s)" % e)
print("\n".join(lines))
alert("Installation", ("Python libraries are successfully imported!\n\n" if ok else "Installation incomplete.\n\n")
      + "\n".join(lines))
