"""Colors of the TBIM visualizations (pure Python, IronPython and CPython)."""

# Categorical palette (distinguishable, colorblind-aware first 8 colors)
PALETTE = [
    (0, 114, 178), (230, 159, 0), (0, 158, 115), (204, 121, 167), (86, 180, 233),
    (213, 94, 0), (240, 228, 66), (120, 94, 240), (153, 153, 153), (0, 102, 102),
    (166, 86, 40), (102, 194, 165), (252, 141, 98), (141, 160, 203), (231, 138, 195),
    (166, 216, 84), (255, 217, 47), (229, 196, 148),
]

# Sequential palette (yellow to red) for numeric classes: readable in shaded views,
# and high values (e.g. U-values, loads) read as "hot"
SEQUENTIAL = [(255, 237, 160), (254, 204, 92), (253, 159, 61), (240, 101, 41), (215, 48, 31), (153, 0, 13)]

# Face topological types and apertures, as in the figures of the paper
TOPOLOGY_COLORS = {
    "extVer": (217, 95, 2),
    "intVer": (253, 191, 111),
    "topHor": (27, 158, 119),
    "botHor": (117, 112, 179),
    "intHor": (166, 206, 227),
    "extInc": (231, 41, 138),
    "intInc": (251, 154, 153),
    "window": (31, 120, 180),
    "door": (106, 61, 154),
}

GRAPH_EDGE_COLORS = {"door": (227, 26, 28), "wall": (120, 120, 120), "slab": (51, 160, 44)}


def to_hex(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classes(values, n=len(SEQUENTIAL)):
    """Equal-interval classes of numeric ``values``: [(label, low, high)]."""
    nums = sorted(set(number(v) for v in values if number(v) is not None))
    if not nums:
        return []
    low, high = nums[0], nums[-1]
    if low == high:
        return [("%g" % low, low, high)]
    step = (high - low) / float(n)
    return [("%g - %g" % (round(low + i * step, 2), round(low + (i + 1) * step, 2)),
             low + i * step, low + (i + 1) * step) for i in range(n)]


def legend_for(values, numeric_threshold=8):
    """Map property values to colors. Return (color of a value function, [(label, rgb)]).

    Numeric properties with more than ``numeric_threshold`` distinct values are
    split in equal-interval classes of a sequential palette; the other values get
    categorical colors (in order of first appearance).
    """
    distinct = []
    for v in values:
        key = "NaN" if v is None else str(v)
        if key not in distinct:
            distinct.append(key)
    numeric = [v for v in distinct if number(v) is not None]
    if len(numeric) == len(distinct) and len(distinct) > numeric_threshold:
        bins = classes(numeric)

        def color_of(value):
            x = number(value)
            for i, (_, lo, hi) in enumerate(bins):
                if x is not None and (lo <= x <= hi or i == len(bins) - 1 and x > hi):
                    return SEQUENTIAL[i % len(SEQUENTIAL)]
            return PALETTE[8]
        return color_of, [(label, SEQUENTIAL[i % len(SEQUENTIAL)]) for i, (label, _, _) in enumerate(bins)]

    ordered = sorted(distinct, key=lambda v: (number(v) is None, number(v), v))
    mapping = dict((v, PALETTE[i % len(PALETTE)]) for i, v in enumerate(ordered))

    def color_of(value):
        return mapping.get("NaN" if value is None else str(value), PALETTE[8])
    return color_of, [(v, mapping[v]) for v in ordered]
