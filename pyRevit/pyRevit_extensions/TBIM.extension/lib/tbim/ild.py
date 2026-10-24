"""Informational Load Dictionaries (ILDs).

An ILD is a dictionary of space properties keyed by ``pr_OccupancyType``. The
ILD file is a JSON list of ILDs; the ``Default`` ILD is used for cells without a
(known) occupancy type.
"""
from tbim import paths
from tbim.jsonio import read_json, write_json

OCCUPANCY_KEY = "pr_OccupancyType"
DEFAULT_OCCUPANCY = "Default"


def load(path=None):
    return read_json(path or paths.data_file(paths.ILDS))


def save(ilds, path=None):
    return write_json(path or paths.data_file(paths.ILDS), ilds)


def occupancy_types(ilds):
    return sorted(set(ild[OCCUPANCY_KEY] for ild in ilds))


def by_occupancy_type(ilds, occupancy_type):
    for ild in ilds:
        if ild.get(OCCUPANCY_KEY) == occupancy_type:
            return ild
    return None


def resolve(ilds, occupancy_type):
    """Return (occupancy type, index, ILD), falling back to the Default ILD."""
    for index, ild in enumerate(ilds):
        if ild.get(OCCUPANCY_KEY) == occupancy_type:
            return occupancy_type, index, ild
    for index, ild in enumerate(ilds):
        if ild.get(OCCUPANCY_KEY) == DEFAULT_OCCUPANCY:
            return DEFAULT_OCCUPANCY, index, ild
    raise KeyError("No ILD for '%s' and no '%s' ILD" % (occupancy_type, DEFAULT_OCCUPANCY))


def load_keys(ilds):
    """All the property names defined by the ILDs (except the occupancy type)."""
    keys = set()
    for ild in ilds:
        keys.update(k for k in ild if k != OCCUPANCY_KEY)
    return sorted(keys)


def coerce_like(text, template):
    """Convert user input ``text`` to the type of the ``template`` value."""
    if isinstance(template, bool):
        value = text.strip().lower()
        if value in ("true", "1", "yes", "y"):
            return True
        if value in ("false", "0", "no", "n"):
            return False
        raise ValueError("'%s' is not a boolean" % text)
    if isinstance(template, int):
        return int(text)
    if isinstance(template, float):
        return float(text)
    return text


def load_assignments(path=None):
    """{cell UID: occupancy type} exported by the Assignment commands."""
    data = read_json(path or paths.data_file(paths.OCCUPANCY_ASSIGNMENTS), default=[])
    return dict((item["UID"], item[OCCUPANCY_KEY]) for item in data)


def save_assignments(assignments, path=None):
    data = [{"UID": uid, OCCUPANCY_KEY: occ} for uid, occ in sorted(assignments.items())]
    return write_json(path or paths.data_file(paths.OCCUPANCY_ASSIGNMENTS), data)
