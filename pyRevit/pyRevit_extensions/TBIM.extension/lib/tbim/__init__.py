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

__version__ = "3.2.0"


BACKEND_ENV_VAR = "TOPOLOGICPY_CORE_BACKEND"  # read by topologicpy.Core: auto, pythonocc or topologic_core
_dll_directories = []  # handles of os.add_dll_directory: the folder is dropped when its handle is closed


def site_packages_dirs():
    """Folders searched for third-party packages (topologicpy, honeybee-energy).

    Install them with ``pip install --target <folder> -r requirements.txt`` in:
    'site_packages' of tbim_settings.json, <tbim>/site-packages or
    %LOCALAPPDATA%/tbim/site-packages (outside synced folders, e.g. OneDrive).
    """
    from tbim import paths
    candidates = [paths.read_settings().get("site_packages"),
                  os.path.join(paths.tbim_root(), "site-packages"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "tbim", "site-packages")]
    return [os.path.join(paths.tbim_root(), c) for c in candidates if c]


def occ_env():
    """The conda environment with pythonocc-core, the geometry kernel of topologicpy (None if not found).

    pythonocc-core is published on conda-forge only: create the environment with ``environment.yml`` in
    'occ_env' of tbim_settings.json or in %LOCALAPPDATA%/tbim/occ-env.
    """
    from tbim import paths
    candidates = [paths.read_settings().get("occ_env"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "tbim", "occ-env")]
    for candidate in candidates:
        if candidate:
            folder = os.path.join(paths.tbim_root(), candidate)
            if os.path.isdir(os.path.join(folder, "Lib", "site-packages", "OCC")):
                return folder
    return None


def _add_occ_env():
    """Make pythonocc importable: its DLLs (OpenCASCADE) in Library/bin, its package in Lib/site-packages.

    The pip folders come first, so numpy and the other packages are the ones of requirements.txt.
    """
    env = occ_env()
    if env is None:
        return
    library = os.path.join(env, "Library", "bin")
    if hasattr(os, "add_dll_directory") and os.path.isdir(library):
        _dll_directories.append(os.add_dll_directory(library))
    site = os.path.join(env, "Lib", "site-packages")
    if site not in sys.path:
        sys.path.append(site)


def add_site_packages():
    """Put the third-party folders on sys.path for the packages imported later (e.g. honeybee by the TBEM).

    The CPython engine of pyRevit lives as long as Revit: the finders keep the folder listings they read
    first, and a package not imported yet is reported missing until their caches are invalidated.
    The topologicpy backend is 'topologic_backend' of tbim_settings.json, else TOPOLOGICPY_CORE_BACKEND, else
    'auto' (pythonocc, topologic_core if pythonocc is missing); topologicpy reads it once, at its first use.
    """
    if sys.version_info[0] < 3:
        return  # IronPython 2.7 commands do not use binary packages
    import importlib

    from tbim import paths
    for site in site_packages_dirs():
        if os.path.isdir(site) and site not in sys.path:
            sys.path.append(site)
    _add_occ_env()
    backend = paths.read_settings().get("topologic_backend")
    if backend:
        os.environ[BACKEND_ENV_VAR] = backend
    else:
        os.environ.setdefault(BACKEND_ENV_VAR, "auto")
    importlib.invalidate_caches()


def topologic_backend():
    """Name of the active topologicpy backend ('PythonOCCBackend', 'TopologicCoreBackend'), None without one."""
    try:
        from topologicpy.Core import Core
        return Core.Backend().__class__.__name__
    except Exception:
        return None


add_site_packages()
