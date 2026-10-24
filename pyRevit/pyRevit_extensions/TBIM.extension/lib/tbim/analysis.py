"""Pure geometric/semantic helpers (no topologicpy, no Revit)."""
import math

EXPOSURES = ["N", "NW", "W", "SW", "S", "SE", "E", "NE"]


def rotate_z(angle_deg, vector=(0.0, 1.0, 0.0)):
    """Rotate a vector around Z. Positive angles are counterclockwise."""
    a = math.radians(angle_deg)
    x, y, z = vector
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)


def exposure(normal, north):
    """Cardinal exposure (8 sectors) of a horizontal direction w.r.t. the north vector.

    The angle is measured counterclockwise from north, so 90 degrees is West.
    """
    angle = math.degrees(math.atan2(normal[1], normal[0]) - math.atan2(north[1], north[0])) % 360.0
    return EXPOSURES[int(((angle + 22.5) % 360.0) // 45.0)]


def dominant(labels, weights):
    """Label with the largest summed weight (first one on ties); None if empty."""
    totals = {}
    order = []
    for label, weight in zip(labels, weights):
        if label not in totals:
            totals[label] = 0.0
            order.append(label)
        totals[label] += weight
    if not order:
        return None
    best = max(totals[label] for label in order)
    return [label for label in order if totals[label] == best][0]


def join_values(values, separator="-"):
    """Combine the values of the cells adjacent to a face: sorted and '-' separated."""
    return separator.join(sorted(str(v) for v in values))


def join_unique(values, separator="-"):
    return join_values(set(str(v) for v in values), separator)


def storey_suffix(storey_name):
    """'BuildingStorey_335cm' -> '335'."""
    if not storey_name:
        return "None"
    tail = str(storey_name).split("_")[-1]
    return tail[:-2] if tail.endswith("cm") else tail
