"""Informational Rule Sets (IRSs).

An IRS is a flat dictionary of conditions and styles::

    {"cnFC_equalTo_pr_TopologicalType": "intVer",
     "cnFC_contains_rl_HasLocation_tpBS": "_0cm",
     "stFC_WallTypeName": "VQ-D1_I"}

Keys starting with ``cn`` are conditions ``cn<target>_<rule>_<property>``; every
other key is a style assigned to the faces matching all the conditions. Rule
sets are applied in order, so later rule sets override earlier styles.
"""
from tbim import paths
from tbim.jsonio import read_json

CONDITION_PREFIX = "cn"
STYLE_PREFIX = "st"
CONDITION_TYPES = ["equalTo", "notEqualTo", "minorOf", "majorOf", "isContained", "contains"]
_RULES = dict((name.lower(), name) for name in CONDITION_TYPES)


def load(irs_paths=None):
    """Load and concatenate the rule sets of all the face types."""
    rulesets = []
    for path in irs_paths or [p for _, p in paths.irs_files()]:
        rulesets.extend(read_json(path, default=[]))
    return rulesets


def split(ruleset):
    """Return (conditions, styles) as lists of (key, value)."""
    conditions, styles = [], []
    for key, value in ruleset.items():
        (conditions if key.startswith(CONDITION_PREFIX) else styles).append((key, value))
    return conditions, styles


def parse_condition(key):
    """'cnFC_equalTo_pr_TopologicalType' -> ('equalTo', 'pr_TopologicalType')."""
    parts = key.split("_")
    if len(parts) < 3:
        raise ValueError("Invalid condition '%s'" % key)
    rule = _RULES.get(parts[1].lower())
    if rule is None:
        raise ValueError("Invalid condition rule '%s' in '%s'" % (parts[1], key))
    return rule, "_".join(parts[2:])


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check(rule, expected, actual):
    """Evaluate one condition. A missing property never satisfies a condition."""
    if actual is None or actual == "":
        return False
    if rule == "equalTo":
        return str(expected) == str(actual)
    if rule == "notEqualTo":
        return str(expected) != str(actual)
    if rule in ("minorOf", "majorOf"):
        a, e = _as_float(actual), _as_float(expected)
        if a is None or e is None:
            return False
        return a < e if rule == "minorOf" else a > e
    if rule == "contains":
        return str(expected) in str(actual)
    if rule == "isContained":
        if isinstance(expected, (list, tuple)):
            return actual in expected or str(actual) in [str(v) for v in expected]
        return str(actual) in str(expected)
    raise ValueError("Unknown rule '%s'" % rule)


def matches(ruleset, properties):
    conditions, _ = split(ruleset)
    for key, expected in conditions:
        rule, prop = parse_condition(key)
        if not check(rule, expected, properties.get(prop)):
            return False
    return True


def apply(rulesets, properties):
    """Return a copy of ``properties`` with the styles of all matching rule sets."""
    result = dict(properties)
    for ruleset in rulesets:
        if matches(ruleset, properties):
            for key, value in split(ruleset)[1]:
                result[key] = value
    return result


def style_keys(rulesets):
    return sorted(set(k for rs in rulesets for k, _ in split(rs)[1]))
