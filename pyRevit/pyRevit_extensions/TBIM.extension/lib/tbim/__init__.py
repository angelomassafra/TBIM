"""TBIM - Topological BIM for building performance management.

Shared library of the TBIM pyRevit extension. Modules are split in:

- engine-agnostic, pure Python (``paths``, ``jsonio``, ``units``, ``ild``, ``irs``,
  ``analysis``, ``zoning``, ``tbimjson``): importable from IronPython and CPython;
- topologicpy based (``topo``, ``loads``, ``styles``, ``instancebim``): CPython only;
- Revit API based (``revit``): requires the Revit API (pyRevit runtime).

Modules keep Python 2.7 compatible syntax where they may be imported by
IronPython scripts.
"""
import os
import sys

__version__ = "1.0.0"


def site_packages_dirs():
    """Folders searched for third-party packages (topologicpy, topologic_core).

    Install them with ``pip install --target <folder> -r requirements.txt`` in:
    'site_packages' of tbim_settings.json, <tbim>/site-packages or
    %LOCALAPPDATA%/tbim/site-packages (outside synced folders, e.g. OneDrive).
    """
    from tbim import paths
    candidates = [paths.read_settings().get("site_packages"),
                  os.path.join(paths.tbim_root(), "site-packages"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "tbim", "site-packages")]
    return [os.path.join(paths.tbim_root(), c) for c in candidates if c]


def _add_site_packages():
    if sys.version_info[0] < 3:
        return  # IronPython 2.7 commands do not use binary packages
    for site in site_packages_dirs():
        if os.path.isdir(site) and site not in sys.path:
            sys.path.append(site)


_add_site_packages()
