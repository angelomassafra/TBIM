"""Results of an EnergyPlus run of a TBEM level (pure Python).

The hourly CSV of ReadVarsESO has a column per output variable and key, e.g.
'ZONE3_BS0 IDEAL LOADS AIR SYSTEM:Zone Ideal Loads Supply Air Total Heating Energy [J](Hourly)'. Annual totals
are summed per zone (kWh) and normalised by the zone floor area (kWh/m2); each cell takes the values of its zone.
The KPIs and every zone output variable can be mapped (``metrics``: {result key: label}).
As in digitman_bim2bem (KPI), heating and cooling are the ideal-load supply-air energies.
"""
import csv
import io

J_TO_KWH = 1.0 / 3.6e6

# (result key, EnergyPlus output variable)
END_USES = [
    ("heating", "Zone Ideal Loads Supply Air Total Heating Energy"),
    ("cooling", "Zone Ideal Loads Supply Air Total Cooling Energy"),
    ("lighting", "Zone Lights Electricity Energy"),
    ("equipment", "Zone Electric Equipment Electricity Energy"),
]
MEANS = [("mean_air_temperature", "Zone Mean Air Temperature")]
END_USE_COLORS = {"heating": (215, 48, 31), "cooling": (31, 120, 180), "lighting": (240, 190, 30),
                  "equipment": (120, 120, 120)}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Revit space parameters written by Results > Write to Spaces: (parameter, result key)
CELL_KEYS = [("rs_HeatingNeed", "heating_per_m2"), ("rs_CoolingNeed", "cooling_per_m2"),
             ("rs_LightingUse", "lighting_per_m2"), ("rs_EquipmentUse", "equipment_per_m2"),
             ("rs_MeanAirTemperature", "mean_air_temperature"), ("rs_EnergyZone", "zone")]
LABELS = {"heating_per_m2": "Heating need (kWh/m2 y)", "cooling_per_m2": "Cooling need (kWh/m2 y)",
          "lighting_per_m2": "Lighting (kWh/m2 y)", "equipment_per_m2": "Equipment (kWh/m2 y)",
          "mean_air_temperature": "Mean air temperature (C)"}


def column_zone(key, zone_names):
    """Zone of a column key (zone names are upper case in EnergyPlus); the longest matching name wins."""
    key = key.strip().upper()
    best = None
    for name in zone_names:
        upper = name.upper()
        if key == upper or key.startswith(upper + " ") or key.startswith(upper + ".."):
            if best is None or len(name) > len(best):
                best = name
    return best


def parse_title(title):
    """(key, variable, unit) of a CSV column title 'KEY:Variable [unit](Hourly)', or None."""
    if ":" not in title or "[" not in title:
        return None
    key, rest = title.split(":", 1)
    variable, unit = rest.split("[", 1)
    return key, variable.strip(), unit.split("]", 1)[0].strip()


def read(csv_path, zone_summary):
    """{'zones': {zone: values}, 'building': values, 'metrics': {key: label}} from the CSV and the zone summary
    of the model. Besides the KPIs (end uses, mean air temperature) every zone output variable is summarised:
    energies [J] as annual kWh and kWh/m2, the others as annual mean and maximum (``metrics``)."""
    names = list(zone_summary)
    sums, peaks = {}, {}  # {(zone, variable): value}
    units = {}
    monthly = dict((key, [0.0] * 12) for key, _ in END_USES)
    end_use_of = dict((name, key) for key, name in END_USES)
    with io.open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader)
        columns = []
        for index, title in enumerate(header[1:], 1):
            parsed = parse_title(title)
            zone = column_zone(parsed[0], names) if parsed else None
            if zone:
                columns.append((index, zone, parsed[1]))
                units[parsed[1]] = parsed[2]
        hours = 0
        for row in reader:
            hours += 1
            month = month_of(row[0])
            for index, zone, variable in columns:
                try:
                    value = float(row[index])
                except (ValueError, IndexError):
                    continue
                sums[zone, variable] = sums.get((zone, variable), 0.0) + value
                peaks[zone, variable] = max(peaks.get((zone, variable), value), value)
                if variable in end_use_of and month:
                    monthly[end_use_of[variable]][month - 1] += value
    metrics = dict(LABELS)
    for variable in sorted(units):
        for suffix, label in metric_labels(variable, units[variable]):
            metrics["%s|%s" % (variable, suffix)] = label
    zones = {}
    for zone in names:
        area = zone_summary[zone].get("floor_area") or 0.0
        out = {"floor_area": area}
        for key, name in END_USES:
            out[key] = round(sums.get((zone, name), 0.0) * J_TO_KWH, 2)
            out[key + "_per_m2"] = round(out[key] / area, 2) if area else 0.0
        for key, name in MEANS:
            out[key] = round(sums[zone, name] / hours, 2) if hours and (zone, name) in sums else None
        for variable, unit in units.items():
            if (zone, variable) not in sums:
                continue
            total, peak = sums[zone, variable], peaks[zone, variable]
            if unit == "J":
                out[variable + "|kWh"] = round(total * J_TO_KWH, 2)
                out[variable + "|kWh/m2"] = round(total * J_TO_KWH / area, 2) if area else None
            else:
                out[variable + "|mean"] = round(total / hours, 2) if hours else None
                out[variable + "|max"] = round(peak, 2)
        zones[zone] = out
    area = sum(z["floor_area"] for z in zones.values())
    building = {"floor_area": round(area, 2), "hours": hours}
    for key, _ in END_USES:
        building[key] = round(sum(z[key] for z in zones.values()), 1)
        building[key + "_per_m2"] = round(building[key] / area, 2) if area else 0.0
    building["monthly"] = dict((key, [round(v * J_TO_KWH, 1) for v in values]) for key, values in monthly.items())
    return {"zones": zones, "building": building, "metrics": metrics}


def metric_labels(variable, unit):
    """[(suffix, label)] of the map metrics of an output variable."""
    if unit == "J":
        return [("kWh/m2", "%s (kWh/m2 y)" % variable), ("kWh", "%s (kWh y)" % variable)]
    shown = " (%s)" % unit if unit else ""
    return [("mean", "%s - annual mean%s" % (variable, shown)), ("max", "%s - maximum%s" % (variable, shown))]


def month_of(date_time):
    """Month of a ReadVarsESO time stamp (' 01/31  24:00:00'), or None."""
    try:
        return int(date_time.strip().split("/")[0])
    except (ValueError, IndexError):
        return None


def zone_series(results, keys=("heating", "cooling")):
    """(zones sorted by heating need, {key: [kWh/m2 of each zone]}) for the charts."""
    zones = sorted(results["zones"], key=lambda z: -results["zones"][z]["heating_per_m2"])
    return zones, dict((key, [results["zones"][z][key + "_per_m2"] for z in zones]) for key in keys)


def level_series(results_by_title):
    """(end uses, {level title: [kWh/m2 of each end use]}) to compare the levels of detail."""
    keys = [key for key, _ in END_USES]
    return keys, dict((title, [r["building"][key + "_per_m2"] for key in keys])
                      for title, r in results_by_title.items())


def by_cell(results, zone_summary):
    """{cell UID: {Revit parameter: value}} - each cell takes the values of its zone."""
    out = {}
    for zone, summary in zone_summary.items():
        values = dict(results["zones"].get(zone, {}), zone=zone)
        for uid in summary["cells"]:
            out[uid] = dict((parameter, values.get(key)) for parameter, key in CELL_KEYS)
    return out


def summary_lines(results, level_title):
    b = results["building"]
    lines = ["%s: %.1f m2 of conditioned and unconditioned zones, %d hours" % (level_title, b["floor_area"],
                                                                            b["hours"])]
    for key, _ in END_USES:
        lines.append("  %-10s %10.0f kWh   %7.1f kWh/m2" % (key.capitalize(), b[key], b[key + "_per_m2"]))
    ranked = sorted(results["zones"].items(), key=lambda item: -item[1]["heating_per_m2"])
    lines.append("Zones with the highest heating need (kWh/m2):")
    lines += ["  %s: %.1f" % (zone, values["heating_per_m2"]) for zone, values in ranked[:8]]
    return lines
