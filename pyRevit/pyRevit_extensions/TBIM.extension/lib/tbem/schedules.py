"""Library of schedules: Honeybee ScheduleRuleset dictionaries (CPython only).

``tbem_Schedules.json`` is a list of ScheduleRuleset dictionaries, the format of the schedule files of
digitman_bim2bem (e.g. Schedules_Occupancy_PoliMi_LC.json, from the university booking service): ``import_file``
adds such files to the library. Identifiers follow digitman: OccSch_, LghSch_, EqpSch_ (fractions of the peak
load), HtnSch_, ClnSch_, VntSch_ (availability of heating, cooling and ventilation).

``default_library`` writes neutral profiles by space category: weekly patterns, heating season 15 Oct - 15 Apr
and cooling season 1 Jun - 15 Sep (Italian climatic zone E).
"""
import copy

from honeybee_energy.lib.scheduletypelimits import fractional, humidity, on_off, temperature
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from ladybug.dt import Date, Time

from tbim.jsonio import read_json

PREFIXES = {"Occupancy": "OccSch_", "Lighting": "LghSch_", "Equipment": "EqpSch_", "Heating": "HtnSch_",
            "Cooling": "ClnSch_", "Ventilation": "VntSch_"}
HEATING_SEASON = [((1, 1), (4, 15)), ((10, 15), (12, 31))]
COOLING_SEASON = [((6, 1), (9, 15))]
YEAR = [((1, 1), (12, 31))]

# Daily profiles: [(until hour, value)] for weekdays, Saturdays and Sundays
OFF = [(24, 0.0)]
PROFILES = {
    "Education": ([(8, 0.0), (13, 1.0), (14, 0.5), (17, 0.8), (19, 0.2), (24, 0.0)], OFF, OFF),
    "Office": ([(7, 0.0), (8, 0.3), (12, 0.9), (14, 0.5), (18, 0.9), (20, 0.2), (24, 0.0)],
               [(8, 0.0), (13, 0.2), (24, 0.0)], OFF),
    "Residential": ([(7, 1.0), (9, 0.5), (17, 0.2), (23, 0.8), (24, 1.0)],) * 3,
    "Retail": ([(9, 0.0), (20, 0.7), (24, 0.0)], [(9, 0.0), (20, 0.9), (24, 0.0)], OFF),
    "Assembly": ([(9, 0.0), (18, 0.3), (24, 0.0)], OFF, OFF),
    "Circulation": ([(7, 0.0), (19, 0.1), (24, 0.0)], [(8, 0.0), (13, 0.05), (24, 0.0)], OFF),
}
# Availability: [(until hour, 0/1)] for weekdays, Saturdays and Sundays
WEEKDAYS_7_18 = ([(7, 0), (18, 1), (24, 0)], OFF, OFF)
MON_SAT_8_21 = ([(8, 0), (21, 1), (24, 0)], [(8, 0), (21, 1), (24, 0)], OFF)
ALL_HOURS = ([(24, 1)],) * 3
AVAILABILITY = [
    ("HtnSch_Season", ALL_HOURS, HEATING_SEASON),
    ("HtnSch_Season_Weekdays_7-18", WEEKDAYS_7_18, HEATING_SEASON),
    ("HtnSch_Season_Mon-Sat_8-21", MON_SAT_8_21, HEATING_SEASON),
    ("ClnSch_Season", ALL_HOURS, COOLING_SEASON),
    ("ClnSch_Season_Weekdays_7-18", WEEKDAYS_7_18, COOLING_SEASON),
    ("ClnSch_Season_Mon-Sat_8-21", MON_SAT_8_21, COOLING_SEASON),
    ("VntSch_Weekdays_7-18", WEEKDAYS_7_18, YEAR),
    ("VntSch_Mon-Sat_8-21", MON_SAT_8_21, YEAR),
]


def day(identifier, steps):
    """ScheduleDay from [(until hour, value)]."""
    times, values, start = [], [], 0
    for until, v in steps:
        times.append(Time(start, 0))
        values.append(v)
        start = until
    return ScheduleDay(identifier, values, times)


def weekly(identifier, profile, periods, type_limit):
    """ScheduleRuleset: the weekly ``profile`` (weekdays, Saturday, Sunday) in the ``periods``, off outside."""
    weekdays, saturday, sunday = profile
    rules = []
    for index, (start, end) in enumerate(periods):
        for name, steps, days in (("Weekdays", weekdays, {"apply_weekday": True}),
                                  ("Saturday", saturday, {"apply_saturday": True}),
                                  ("Sunday", sunday, {"apply_sunday": True})):
            rule = ScheduleRule(day("%s_%s%d" % (identifier, name, index), steps),
                                start_date=Date(*start), end_date=Date(*end))
            for attribute in days:
                setattr(rule, attribute, True)
            rules.append(rule)
    return ScheduleRuleset(identifier, day("%s_Off" % identifier, OFF), rules, type_limit)


def default_library():
    """[ScheduleRuleset dictionaries] of the neutral library (see the module docstring)."""
    library = [ScheduleRuleset.from_constant_value("AlwaysOn", 1, fractional),
               ScheduleRuleset.from_constant_value("AlwaysOff", 0, fractional)]
    for name, profile in sorted(PROFILES.items()):
        for use in ("Occupancy", "Lighting", "Equipment"):
            library.append(weekly(PREFIXES[use] + name, profile, YEAR, fractional))
    for identifier, profile, periods in AVAILABILITY:
        library.append(weekly(identifier, profile, periods, on_off))
    return [s.to_dict() for s in library]


def normalized(schedule, prefix=None):
    """ScheduleRuleset dictionary of a digitman schedule file entry (identifier prefix, type limit, rules)."""
    schedule = copy.deepcopy(schedule)
    schedule["type"] = "ScheduleRuleset"
    if prefix and not schedule["identifier"].startswith(prefix):
        schedule["identifier"] = prefix + schedule["identifier"]
    schedule.setdefault("schedule_type_limit", fractional.to_dict())
    for day_schedule in schedule.get("day_schedules", []):
        day_schedule["type"] = "ScheduleDay"
        times = day_schedule["times"]
        if len(times) == 1 and len(times[0]) == len(day_schedule["values"]) > 2:
            times = [[hour, 0] for hour in times[0]]  # some digitman files list the hours in one item
        day_schedule["times"] = [list(t)[:2] for t in times]
    for rule in schedule.get("schedule_rules", []):
        rule["type"] = "ScheduleRuleAbridged"
        rule["start_date"], rule["end_date"] = list(rule["start_date"])[:2], list(rule["end_date"])[:2]
    return schedule


def import_file(path, use=None):
    """ScheduleRuleset dictionaries of a JSON file (one or a list); ``use`` (e.g. 'Occupancy') sets the prefix."""
    data = read_json(path)
    entries = data if isinstance(data, list) else [data]
    return [normalized(s, PREFIXES.get(use)) for s in entries]


def merge(library, new):
    """Library with the ``new`` schedules (same identifier: replaced)."""
    identifiers = set(s["identifier"] for s in new)
    return [s for s in library if s["identifier"] not in identifiers] + list(new)


def rulesets(library):
    """{identifier: ScheduleRuleset}."""
    return dict((s["identifier"], ScheduleRuleset.from_dict(normalized(s))) for s in library)


def constant(identifier, value, kind="temperature"):
    limits = {"temperature": temperature, "humidity": humidity, "fraction": fractional}[kind]
    return ScheduleRuleset.from_constant_value(identifier, value, limits)
