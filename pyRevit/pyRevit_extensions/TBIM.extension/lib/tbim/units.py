"""Unit conversions. Topologic models are in centimetres, Revit internal units are feet."""

CM_PER_FT = 30.48


def cm_to_ft(cm):
    return cm / CM_PER_FT


def ft_to_cm(ft):
    return ft * CM_PER_FT


def ft2_to_m2(ft2):
    return ft2 * 0.09290304


def ft3_to_m3(ft3):
    return ft3 * 0.028316846592


def cm2_to_m2(cm2):
    return cm2 / 1.0e4


def cm3_to_m3(cm3):
    return cm3 / 1.0e6
