"""TBIM - Topological BIM for building performance management.

Shared library of the TBIM pyRevit extension. Modules are split in:

- engine-agnostic, pure Python (``paths``, ``projects``, ``jsonio``, ``units``, ``colors``, ``ild``,
  ``irs``, ``ibim``, ``analysis``, ``zoning``, ``tbimjson``, ``materials``): importable from
  IronPython and CPython, and outside Revit;
- topologicpy based, no Revit (``topo``, ``controllers``, ``loads``, ``styles``, ``apertures``,
  ``rooms``, ``instancebim``, ``scene``, ``export``): CPython only, used by the offline demo and tests;
- Revit API based (``revit``, ``ui``, ``assignment``, ``ifc``, ``collectors``, ``revit_types``,
  ``visualize``, ``check``, ``pipeline``): require the Revit API (pyRevit runtime); ``pipeline`` holds
  the steps of the workflow shared by the ribbon commands and Project > Run.

Modules keep Python 2.7 compatible syntax where they may be imported by
IronPython scripts.
"""
import os
import sys

__version__ = "3.1.1"


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


def add_site_packages():
    """Put the third-party folders on sys.path for the packages imported later (e.g. honeybee by the TBEM).

    The CPython engine of pyRevit lives as long as Revit: the finders keep the folder listings they read
    first, and a package not imported yet is reported missing until their caches are invalidated.
    """
    if sys.version_info[0] < 3:
        return  # IronPython 2.7 commands do not use binary packages
    import importlib
    for site in site_packages_dirs():
        if os.path.isdir(site) and site not in sys.path:
            sys.path.append(site)
    importlib.invalidate_caches()


add_site_packages()
