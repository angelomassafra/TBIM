"""Files of the TBEM (pure Python): the ``bem`` folder of the active TBIM project.

    <project>/
      json/                          <- TBIM data (the source of the conversion)
      bem/
        tbem_Settings.json           <- settings of the conversion and of the simulation
        tbem_Programs.json           <- BEM data by occupancy type (loads, set-points, schedules)
        tbem_Schedules.json          <- library of schedules (Honeybee ScheduleRuleset dictionaries)
        tbem_Zones.json              <- thermal zones of the cells, when changed in the TBEM tab
        tbem_<level>.hbjson          <- Honeybee model of a level (SpatialBEM, TopologicalBEM, FullTBEM)
        tbem_<level>_Zones.json      <- zones of the model: cells, floor area, volume
        tbem_<level>.idf             <- EnergyPlus model
        tbem_<level>_Results.json    <- annual results by zone
        simulation/<level>/          <- EnergyPlus outputs (csv, err, eio, html)
        weather/, shades/            <- EPW/DDY files and BRep shading geometry

EnergyPlus runs in %LOCALAPPDATA%/tbim/energyplus/<project>/<level>: its post-processor (ReadVarsESO) fails on
paths with non-ASCII characters, common in synced folders.
"""
import os
import re
import shutil

from tbim import paths, projects

BEM_FOLDER = "bem"
SETTINGS = "tbem_Settings.json"
PROGRAMS = "tbem_Programs.json"
SCHEDULES = "tbem_Schedules.json"
ZONES = "tbem_Zones.json"
SIMULATION_FOLDER = "simulation"
WEATHER_FOLDER = "weather"
SHADES_FOLDER = "shades"
TEMPLATES = ("templates", "bem")

SPATIAL, TOPOLOGICAL, FULL = "SpatialBEM", "TopologicalBEM", "FullTBEM"
LEVELS = [SPATIAL, TOPOLOGICAL, FULL]
TITLES = {SPATIAL: "Spatial BEM", TOPOLOGICAL: "Topological BEM", FULL: "Full TBEM"}

# TBIM models the conversion starts from, from the most to the least complete
SOURCES = [
    ("InstanceBIM", paths.CC_IBIM),
    ("TopologicalBIM", paths.CC_TBIM),
    ("Informational Styles", paths.CC_STYLES),
    ("Thermal zones", paths.CC_LOADS_CLUSTERIZED),
]


def project_folder():
    """Active TBIM project, or the parent of the data folder."""
    return projects.active_project() or os.path.dirname(os.path.normpath(paths.data_dir()))


def bem_dir():
    return os.path.join(project_folder(), BEM_FOLDER)


def bem_file(name):
    return os.path.join(bem_dir(), name)


def model_file(level):
    return bem_file("tbem_%s.hbjson" % level)


def zones_file(level):
    return bem_file("tbem_%s_Zones.json" % level)


def idf_file(level):
    return bem_file("tbem_%s.idf" % level)


def results_file(level):
    return bem_file("tbem_%s_Results.json" % level)


def simulation_dir(level):
    return os.path.join(bem_dir(), SIMULATION_FOLDER, level)


def templates_dir():
    return os.path.join(paths.tbim_root(), *TEMPLATES)


def ensure(name):
    """Path of a bem file, copied from the templates the first time it is needed."""
    path = bem_file(name)
    template = os.path.join(templates_dir(), name)
    if not os.path.isfile(path) and os.path.isfile(template):
        if not os.path.isdir(bem_dir()):
            os.makedirs(bem_dir())
        shutil.copy(template, path)
    return path


def source_model():
    """(label, path) of the most complete TBIM model of the project, or None."""
    for label, name in SOURCES:
        if os.path.isfile(paths.data_file(name)):
            return label, paths.data_file(name)
    return None


def built_levels():
    """Levels with a Honeybee model, from the most detailed."""
    return [level for level in reversed(LEVELS) if os.path.isfile(model_file(level))]


def ascii_name(text):
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", text).strip("_") or "tbem"


def run_dir(level):
    """Working folder of the EnergyPlus run of ``level`` (ASCII path, outside synced folders)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "tbim", "energyplus", ascii_name(os.path.basename(project_folder())), level)


def resolve(path):
    """Absolute path of a path relative to the bem folder."""
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(bem_dir(), path))


def relative(path):
    """Path relative to the bem folder when inside it ('/' separated), else absolute."""
    rel = os.path.relpath(os.path.abspath(path), bem_dir())
    return os.path.abspath(path) if rel.startswith(os.pardir) else rel.replace(os.sep, "/")


def copy_in(path, folder):
    """Copy ``path`` into the bem sub-folder ``folder`` (unless already there). Return the relative path."""
    target_dir = os.path.join(bem_dir(), folder)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    target = os.path.join(target_dir, os.path.basename(path))
    if os.path.normcase(os.path.abspath(path)) != os.path.normcase(target):
        shutil.copy(path, target)
    return relative(target)
