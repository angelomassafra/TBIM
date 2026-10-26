"""EnergyPlus model and run of a TBEM level (CPython only).

The IDF is written by Honeybee (EnergyPlus 24.2) with the simulation parameters of the settings, the role of
the Eppy edits in digitman_bim2bem: run period, timestep, shadow calculation, output variables and, with the
design days of a DDY file, the sizing of the ideal loads.

EnergyPlus runs in a working folder with an ASCII path (``files.run_dir``), detached from Revit: ``start``
returns at once and ``status`` tells when the run is over; ``collect`` copies the outputs to the project.
"""
import ctypes
import datetime
import os
import shutil
import subprocess

from honeybee_energy.simulation.control import SimulationControl
from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.simulation.runperiod import RunPeriod
from honeybee_energy.simulation.shadowcalculation import ShadowCalculation
from honeybee_energy.simulation.sizing import SizingParameter
from honeybee_energy.writer import energyplus_idf_version
from ladybug.dt import Date

from tbim.jsonio import read_json, write_json

PREFIX = "tbem"
STATUS = "tbem_run.json"
RUNNING, COMPLETED, FAILED, NONE = "running", "completed", "failed", "not run"
OUTPUT_EXTENSIONS = (".csv", ".err", ".eio", ".htm", ".end", ".rdd", ".mtr")


def parameter(settings, north_angle=0.0, ddy_path=None):
    """SimulationParameter of the settings. ``north_angle``: counterclockwise from the Y axis (degrees)."""
    sim = settings["simulation"]
    period = sim["run_period"]
    output = SimulationOutput(outputs=sim["output_variables"], reporting_frequency=sim["reporting_frequency"],
                              include_sqlite=False, include_html=True, summary_reports=["AllSummary"])
    run_period = RunPeriod(Date(*period["start"]), Date(*period["end"]))
    if period.get("start_day_of_week"):
        run_period.start_day_of_week = period["start_day_of_week"]
    control = SimulationControl(do_zone_sizing=bool(ddy_path), do_system_sizing=False, do_plant_sizing=False,
                                run_for_sizing_periods=False, run_for_run_periods=True)
    shadow = ShadowCalculation(solar_distribution=sim["solar_distribution"], calculation_method="PolygonClipping",
                               calculation_update_method="Periodic", calculation_frequency=30,
                               maximum_figures=15000)
    sizing = SizingParameter()
    if ddy_path:
        sizing.add_from_ddy_996_004(ddy_path)
    return SimulationParameter(output, run_period, sim["timestep"], control, shadow, sizing,
                               north_angle=north_angle, terrain_type=sim["terrain"])


def ground_temperatures(epw_path):
    """Site:GroundTemperature:BuildingSurface with the monthly ground temperatures of the EPW at the shallowest
    depth it gives (None if it gives none: EnergyPlus then uses 18 C)."""
    from ladybug.epw import EPW
    by_depth = EPW(epw_path).monthly_ground_temperature
    if not by_depth:
        return None
    depth = min(by_depth)
    temperatures = by_depth[depth]
    values = ",\n ".join("%.2f" % t for t in temperatures.values)
    return "Site:GroundTemperature:BuildingSurface,\n %s;  !- monthly ground temperatures at %g m (EPW)" % (
        values, depth)


def idf_text(model, simulation_parameter, epw_path=None):
    parts = [energyplus_idf_version(), simulation_parameter.to_idf()]
    ground = ground_temperatures(epw_path) if epw_path else None
    return "\n\n".join(parts + ([ground] if ground else []) + [model.to.idf(model)])


def write_idf(model, simulation_parameter, path, epw_path=None):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w") as f:
        f.write(idf_text(model, simulation_parameter, epw_path))
    return path


def _clean(folder):
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                os.remove(path)
    else:
        os.makedirs(folder)


def start(idf_path, epw_path, run_dir, energyplus_folder, wait=False):
    """Run EnergyPlus (ExpandObjects, ReadVarsESO) on copies of the IDF and EPW in ``run_dir``.
    Return the process (finished if ``wait``)."""
    _clean(run_dir)
    shutil.copy(idf_path, os.path.join(run_dir, "in.idf"))
    shutil.copy(epw_path, os.path.join(run_dir, "in.epw"))
    command = [os.path.join(energyplus_folder, "energyplus.exe"), "-w", "in.epw", "-d", run_dir, "-p", PREFIX,
               "-s", "C", "-x", "-r", "in.idf"]
    log = open(os.path.join(run_dir, "energyplus.log"), "w")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = subprocess.Popen(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    write_json(os.path.join(run_dir, STATUS), {"pid": process.pid, "idf": idf_path, "epw": epw_path,
                                               "started": datetime.datetime.now().isoformat(timespec="seconds")})
    if wait:
        process.wait()
        log.close()
    return process


def _alive(pid):
    """True if the process ``pid`` is running (Windows)."""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 259  # STILL_ACTIVE


def end_message(run_dir):
    """Last line of EnergyPlus (e.g. 'EnergyPlus Completed Successfully-- 3 Warning; 0 Severe Errors; ...')."""
    for name in os.listdir(run_dir) if os.path.isdir(run_dir) else []:
        if name.lower().endswith(".end"):
            with open(os.path.join(run_dir, name)) as f:
                return f.read().strip()
    return None


def status(run_dir):
    """(RUNNING | COMPLETED | FAILED | NONE, message)."""
    info = read_json(os.path.join(run_dir, STATUS), default={})
    if not info:
        return NONE, "EnergyPlus has not been run yet."
    message = end_message(run_dir)
    if message is None:
        if _alive(info["pid"]):
            return RUNNING, "EnergyPlus is running (started %s)." % info["started"]
        return FAILED, "EnergyPlus stopped without results: see %s" % os.path.join(run_dir, "energyplus.log")
    if "Completed Successfully" in message and csv_file(run_dir):
        return COMPLETED, message
    return FAILED, message


def csv_file(run_dir):
    """Hourly results (ReadVarsESO) of the run, or None."""
    for name in os.listdir(run_dir):
        if name.startswith(PREFIX) and name.lower().endswith(".csv") and "meter" not in name.lower() \
                and "table" not in name.lower():
            return os.path.join(run_dir, name)
    return None


def collect(run_dir, destination):
    """Copy the outputs of the run to ``destination``. Return the copied paths."""
    if not os.path.isdir(destination):
        os.makedirs(destination)
    copied = []
    for name in os.listdir(run_dir):
        if name.startswith(PREFIX) and name.lower().endswith(OUTPUT_EXTENSIONS):
            shutil.copy(os.path.join(run_dir, name), os.path.join(destination, name))
            copied.append(os.path.join(destination, name))
    return copied
