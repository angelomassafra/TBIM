"""Single source of truth for the TBIM installation folder and data files.

The installation folder is the ancestor directory named ``tbim`` that contains
the pyRevit extension::

    tbim/
      json/                  <- data exchanged between the TBIM commands
      tbim_settings.json     <- optional: {"data_dir": "examples/demo/json"}
      pyRevit/pyRevit_extensions/TBIM.extension/lib/tbim/paths.py

Set the ``TBIM_HOME`` environment variable to use another installation folder.
"""
import os

ROOT_FOLDER_NAME = "tbim"
ENV_VAR = "TBIM_HOME"

# Data files, relative to <tbim>/json
BREP_FILEPATHS = "tbim_BRepFilePaths.json"
NORTH_ANGLE = "tbim_ProjectNorthAngle.json"
CC_CONTROLLERS = "tbim_CellComplex_Controllers.json"
OCCUPANCY_ASSIGNMENTS = "tbim_CellComplex_Loads-OccupancyTypes.json"
ILDS = "tbim_ILDs.json"
CC_LOADS = "tbim_CellComplex_Loads.json"
CC_LOADS_CLUSTERIZED = "tbim_CellComplex_Loads-Clusterized.json"
FACE_PROPERTIES = "tbim__FaceProperties.json"
CC_STYLES = "tbim_CellComplex_Styles.json"
CC_TBIM = "tbim_CellComplex_TBIM.json"
APERTURE_LOCATIONS = "tbim_CellComplex_TBIM_AperturesLocation.json"
CC_IBIM = "tbim_CellComplex_IBIM.json"
IBIM_BY_OCCUPANCY_TYPE = "tbim_InstanceBIM_byOccupancyType.json"
IBIM_BY_TABLE_OF_SPACES = "tbim_InstanceBIM_byTableOfSpaces.json"
SHARED_PARAMETERS = "tbim_SharedParameters.txt"
SETTINGS = "tbim_settings.json"

# Informational Rule Sets, one file per face topological type (applied in this order)
IRS_FILES = [
    ("botHor", "tbim_IRS_botHorFaces.json"),
    ("topHor", "tbim_IRS_topHorFaces.json"),
    ("intHor", "tbim_IRS_intHorFaces.json"),
    ("intVer", "tbim_IRS_intVerFaces.json"),
    ("extVer", "tbim_IRS_extVerFaces.json"),
]


def _find_root(start):
    current = os.path.abspath(start)
    while True:
        if os.path.basename(current).lower() == ROOT_FOLDER_NAME:
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def tbim_root():
    """Return the TBIM installation folder."""
    env = os.environ.get(ENV_VAR)
    if env:
        return os.path.abspath(env)
    # start above this package, which is itself called 'tbim'
    root = _find_root(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root:
        return root
    # Fallback: <root>/pyRevit/pyRevit_extensions/TBIM.extension/lib/tbim
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, *[os.pardir] * 5))


def settings_file():
    return os.path.join(tbim_root(), SETTINGS)


def read_settings():
    import json
    try:
        with open(settings_file()) as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return {}


def write_settings(settings):
    import json
    with open(settings_file(), "w") as f:
        json.dump(settings, f, indent=4)


def data_dir():
    """Data folder: 'data_dir' of tbim_settings.json (absolute or relative to <tbim>) or <tbim>/json."""
    custom = read_settings().get("data_dir")
    if custom:
        return os.path.normpath(os.path.join(tbim_root(), custom))
    return os.path.join(tbim_root(), "json")


def data_file(name):
    """Absolute path of a file in the TBIM data folder."""
    return os.path.join(data_dir(), name)


def shared_parameter_file():
    """Shared parameter file holding the TBIM parameter definitions."""
    return os.path.join(tbim_root(), SHARED_PARAMETERS)


def irs_files():
    """List of (face type, absolute path) of the Informational Rule Sets."""
    return [(face_type, data_file(name)) for face_type, name in IRS_FILES]
