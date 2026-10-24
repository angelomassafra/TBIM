"""Fast, geometry-free reader of topologicpy JSON exports.

Useful when only the dictionaries are needed (e.g. to push data to Revit): it
avoids rebuilding the geometry, which can take tens of seconds.
"""
from tbim.jsonio import read_json

# Keys written by topologicpy itself, not TBIM properties
INTERNAL_KEYS = ("toplevel", "uuid", "__cluster__", "apertures", "type")


def clean(dictionary):
    return dict((k, v) for k, v in (dictionary or {}).items() if k not in INTERNAL_KEYS)


def dictionaries(path_or_records):
    """Return {'Cell': [...], 'Face': [...], 'Aperture': [...]} of cleaned dictionaries."""
    records = read_json(path_or_records) if isinstance(path_or_records, str) else path_or_records
    out = {"Cell": [], "Face": [], "Aperture": []}
    seen = set()
    for record in records:
        kind = record.get("type")
        if kind in ("Cell", "Face") and record.get("dictionary"):
            out[kind].append(clean(record["dictionary"]))
        for group in record.get("apertures") or []:
            for aperture in group:
                d = aperture.get("dictionary")
                if aperture.get("type") == "Face" and d and d.get("UID") not in seen:
                    seen.add(d.get("UID"))  # apertures of internal faces may be repeated
                    out["Aperture"].append(clean(d))
    return out


def aperture_uid(group):
    for item in group:
        if item.get("type") == "Face":
            return (item.get("dictionary") or {}).get("UID")
    return None


def move_apertures(records, moves):
    """Translate in place the apertures {UID: (dx, dy, dz)} by moving their vertices.

    Working on the JSON avoids rebuilding the CellComplex (``Topology.RemoveContent``
    removes all the apertures); the host face is found again on import.
    Return the UIDs of the moved apertures.
    """
    moved = set()
    for record in records:
        for group in record.get("apertures") or []:
            uid = aperture_uid(group)
            if uid not in moves:
                continue
            for item in group:
                if item.get("type") == "Vertex":
                    item["coordinates"] = [c + d for c, d in zip(item["coordinates"], moves[uid])]
            moved.add(uid)
    return sorted(moved)


def aperture_polygons(path_or_records):
    """[(dictionary, [vertex coordinates in boundary order])] of the apertures (unique UIDs)."""
    records = read_json(path_or_records) if isinstance(path_or_records, str) else path_or_records
    out, seen = [], set()
    for record in records:
        for group in record.get("apertures") or []:
            uid = aperture_uid(group)
            if uid is None or uid in seen:
                continue
            seen.add(uid)
            face = [i for i in group if i.get("type") == "Face"][0]
            out.append((clean(face.get("dictionary")), [i["coordinates"] for i in group if i.get("type") == "Vertex"]))
    return out


def by_uid(items):
    return dict((d["UID"], d) for d in items if d.get("UID") is not None)
