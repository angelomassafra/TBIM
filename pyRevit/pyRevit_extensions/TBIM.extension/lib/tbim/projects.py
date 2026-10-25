"""TBIM projects: one folder per project (IronPython and CPython).

A project folder holds the BReps of the 3D model and the data exchanged by the
TBIM commands::

    <projects root>/<name>/
      project.json    <- {"name", "created", "description"}
      3d/             <- BRep files (one per building block)
      json/           <- TBIM data (ILDs, IRSs, CellComplex models, ...)

The projects root is 'projects_root' of tbim_settings.json (absolute or relative
to <tbim>), by default <tbim>/projects. New projects start from the data files
of <tbim>/templates/json. The active project is the 'data_dir' of the settings;
the Revit model stores its project folder in the 'tbim_ProjectFolder' project
parameter, so that opening the model activates its project (hooks/doc-opened.py).
The folder is stored relative to <tbim> when inside it (e.g. 'projects/School'),
so the models of the example projects find their folder on any machine.
"""
import datetime
import os
import re
import shutil

from tbim import paths
from tbim.jsonio import read_json, write_json

PROJECT_FILE = "project.json"
DATA_FOLDER = "json"
MODEL_FOLDER = "3d"
TEMPLATES_FOLDER = "templates"
DEFAULT_ROOT = "projects"
REVIT_PARAMETER = "tbim_ProjectFolder"

# Outputs of the TBIM workflow, in order: (step of the paper, data file)
PIPELINE = [
    ("3D Model", paths.BREP_FILEPATHS),
    ("Informational Controllers", paths.CC_CONTROLLERS),
    ("Occupancy assignment", paths.OCCUPANCY_ASSIGNMENTS),
    ("Informational Loads", paths.CC_LOADS),
    ("Thermal zones", paths.CC_LOADS_CLUSTERIZED),
    ("Informational Styles", paths.CC_STYLES),
    ("TopologicalBIM", paths.CC_TBIM),
    ("InstanceBIM", paths.CC_IBIM),
]


def projects_root():
    root = paths.read_settings().get("projects_root") or DEFAULT_ROOT
    return os.path.normpath(os.path.join(paths.tbim_root(), root))


def templates_dir():
    return os.path.join(paths.tbim_root(), TEMPLATES_FOLDER, DATA_FOLDER)


def is_project(folder):
    return bool(folder) and os.path.isfile(os.path.join(folder, PROJECT_FILE))


def info(folder):
    """project.json of ``folder`` (name defaults to the folder name)."""
    data = read_json(os.path.join(folder, PROJECT_FILE), default={})
    data.setdefault("name", os.path.basename(os.path.normpath(folder)))
    return data


def list_projects(root=None):
    """[(name, folder)] of the projects in the projects root, sorted by name."""
    root = root or projects_root()
    if not os.path.isdir(root):
        return []
    folders = [os.path.join(root, n) for n in os.listdir(root)]
    return sorted((info(f)["name"], f) for f in folders if is_project(f))


def safe_name(name):
    """Folder name for a project name (letters, digits, '-', '_')."""
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", name.strip()).strip("_")


def init_project(folder, name=None, description=""):
    """Make ``folder`` a TBIM project (existing data is kept). Return the folder."""
    for sub in (DATA_FOLDER, MODEL_FOLDER):
        if not os.path.isdir(os.path.join(folder, sub)):
            os.makedirs(os.path.join(folder, sub))
    if not is_project(folder):
        write_json(os.path.join(folder, PROJECT_FILE), {
            "name": name or os.path.basename(os.path.normpath(folder)),
            "created": datetime.date.today().isoformat(),
            "description": description})
    return folder


def create_project(name, description="", root=None, templates=None):
    """Create <root>/<safe name>/ from the templates. Return the project folder."""
    if not safe_name(name):
        raise ValueError("'%s' is not a valid project name." % name)
    folder = os.path.join(root or projects_root(), safe_name(name))
    if os.path.exists(folder):
        raise ValueError("The folder %s already exists." % folder)
    init_project(folder, name, description)
    templates = templates or templates_dir()
    if os.path.isdir(templates):
        for file_name in os.listdir(templates):
            source = os.path.join(templates, file_name)
            if os.path.isfile(source):
                shutil.copy(source, os.path.join(folder, DATA_FOLDER, file_name))
    return folder


def data_dir_of(folder):
    return os.path.join(folder, DATA_FOLDER)


def _relative_to(path, base):
    """``path`` relative to ``base`` ('/' separated) when inside it, else the absolute path."""
    path = os.path.abspath(path)
    try:
        rel = os.path.relpath(path, base)
    except ValueError:  # another drive
        return path
    return path if rel.startswith(os.pardir) else rel.replace(os.sep, "/")


def activate(folder):
    """Make ``folder`` the active project (its json/ becomes the TBIM data folder)."""
    init_project(folder)
    settings = paths.read_settings()
    settings["data_dir"] = _relative_to(data_dir_of(folder), paths.tbim_root())
    paths.write_settings(settings)
    return folder


def active_project():
    """Folder of the active project, or None if the data folder is not in a project."""
    folder = os.path.dirname(os.path.normpath(paths.data_dir()))
    return folder if is_project(folder) else None


def model_link(folder):
    """Value of the Revit parameter for ``folder``: relative to <tbim> when inside it, else absolute."""
    return _relative_to(folder, paths.tbim_root())


def resolve_link(value):
    """Project folder of a stored link (relative links are relative to <tbim>), or None."""
    if not value:
        return None
    return os.path.normpath(value if os.path.isabs(value) else os.path.join(paths.tbim_root(), value))


def resolve(path):
    """Absolute path of a project-relative path (e.g. '3d/BlockA.brep')."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(active_project() or paths.data_dir(), path))


def relative(path):
    """Path relative to the active project when inside it (portable project folders)."""
    folder = active_project()
    return _relative_to(path, folder) if folder else path


def status(folder=None):
    """[(step, file name, exists)] of the workflow outputs of a project."""
    data = data_dir_of(folder) if folder else paths.data_dir()
    return [(step, name, os.path.isfile(os.path.join(data, name))) for step, name in PIPELINE]
