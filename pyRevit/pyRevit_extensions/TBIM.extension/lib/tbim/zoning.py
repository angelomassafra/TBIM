"""Thermal zoning of cells (pure Python, deterministic).

Cells are clustered in thermal zones as follows:

1. classrooms (and ``Volume`` spaces) are zones on their own;
2. public circulation and support/private circulation cells are grouped in
   laterally connected components;
3. the other ("free") cells are clustered with K-Means on ``KMEANS_KEYS`` and each
   cluster is split in laterally connected components;
4. support cells are merged into the laterally adjacent free zones (zones
   sharing a support cell are merged); support cells not adjacent to any free
   zone keep their support zone;
5. zones are named ``Zone<i>_BS<storey elevation>``.
"""
import random

KMEANS_KEYS = ["pr_AreaPerOccupantPeak", "pr_IsHeated", "pr_IsCooled"]
KMEANS_K = 10

CLASSROOM, PUBLIC, SUPPORT, FREE = "classroom", "public", "support", "free"


def classify(props):
    occupancy = props.get("pr_OccupancyType") or "Support:SupportSpaces"
    circulation = props.get("pr_CirculationType") or "NoCirculation"
    if "Classroom" in occupancy or "Volume" in occupancy:
        return CLASSROOM
    if "Public" in circulation:
        return PUBLIC
    if "Private" in circulation or "Support" in occupancy:
        return SUPPORT
    return FREE


def to_number(value):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip().lower()
        return 1.0 if text in ("true", "yes") else 0.0


def _sqdist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def kmeans(points, k, n_init=10, max_iter=300, seed=0):
    """K-Means with k-means++ init. Returns a label per point."""
    n = len(points)
    if n == 0:
        return []
    k = max(1, min(k, len(set(tuple(p) for p in points))))
    rng = random.Random(seed)
    best_labels, best_inertia = None, None
    for _ in range(n_init):
        centroids = [list(points[rng.randrange(n)])]
        while len(centroids) < k:
            d2 = [min(_sqdist(p, c) for c in centroids) for p in points]
            total = sum(d2)
            if total == 0:
                break
            r, acc = rng.random() * total, 0.0
            for i, d in enumerate(d2):
                acc += d
                if acc >= r:
                    centroids.append(list(points[i]))
                    break
        labels = [0] * n
        for _ in range(max_iter):
            new_labels = [min(range(len(centroids)), key=lambda j: _sqdist(p, centroids[j])) for p in points]
            for j in range(len(centroids)):
                members = [points[i] for i in range(n) if new_labels[i] == j]
                if members:
                    centroids[j] = [sum(c) / float(len(members)) for c in zip(*members)]
            if new_labels == labels:
                break
            labels = new_labels
        inertia = sum(_sqdist(points[i], centroids[labels[i]]) for i in range(n))
        if best_inertia is None or inertia < best_inertia:
            best_labels, best_inertia = labels, inertia
    return best_labels


def connected_components(uids, adjacency):
    """Split ``uids`` in groups connected through ``adjacency`` (uid -> set of uids)."""
    remaining = list(uids)
    members = set(uids)
    seen = set()
    groups = []
    for uid in remaining:
        if uid in seen:
            continue
        group, stack = [], [uid]
        seen.add(uid)
        while stack:
            current = stack.pop()
            group.append(current)
            for other in adjacency.get(current, ()):
                if other in members and other not in seen:
                    seen.add(other)
                    stack.append(other)
        groups.append(sorted(group, key=remaining.index))
    return groups


def merge_overlapping(groups):
    """Merge groups sharing at least one element (order preserving)."""
    merged = []
    for group in groups:
        group = list(group)
        overlapping = [m for m in merged if set(m) & set(group)]
        for m in overlapping:
            merged.remove(m)
            group = m + [g for g in group if g not in m]
        merged.append(group)
    return merged


def zones(cells, lateral_adjacency, kmeans_keys=None, k=KMEANS_K):
    """Return {cell UID: 'ZoneCluster<i>'}.

    cells: ordered list of (uid, props); lateral_adjacency: cells sharing a
    vertical face. Zones never span building storeys.
    """
    kmeans_keys = kmeans_keys or KMEANS_KEYS
    kinds = dict((uid, classify(props)) for uid, props in cells)
    by_kind = dict((kind, [uid for uid, _ in cells if kinds[uid] == kind])
                   for kind in (CLASSROOM, PUBLIC, SUPPORT, FREE))

    free_zones = []
    free = by_kind[FREE]
    if free:
        props = dict(cells)
        points = [[to_number(props[uid].get(key)) for key in kmeans_keys] for uid in free]
        labels = kmeans(points, k)
        for label in sorted(set(labels), key=labels.index):
            cluster = [uid for uid, lb in zip(free, labels) if lb == label]
            free_zones.extend(connected_components(cluster, lateral_adjacency))

    support_zones = connected_components(by_kind[SUPPORT], lateral_adjacency)
    public_zones = connected_components(by_kind[PUBLIC], lateral_adjacency)
    classroom_zones = [[uid] for uid in by_kind[CLASSROOM]]

    attached = set()
    extended = []
    for zone in free_zones:
        members = set(zone)
        extra = [uid for uid in by_kind[SUPPORT] if lateral_adjacency.get(uid, set()) & members]
        attached.update(extra)
        extended.append(zone + extra)
    leftover_support = [[uid for uid in z if uid not in attached] for z in support_zones]

    final = merge_overlapping(extended) + [z for z in leftover_support if z] + public_zones + classroom_zones
    result = {}
    for index, zone in enumerate(final):
        for uid in zone:
            result[uid] = "ZoneCluster%d" % index
    return result
