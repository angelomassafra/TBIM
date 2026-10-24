"""Informational Styles: apply the Informational Rule Sets to the faces (CPython only)."""
from topologicpy.CellComplex import CellComplex

from tbim import irs, topo


def run(cc, rulesets):
    """Assign the styles of the matching rule sets to every face. Return the number of styled faces."""
    styled = 0
    for face in CellComplex.Faces(cc):
        props = topo.props(face)
        if "UID" not in props:
            continue
        new_props = irs.apply(rulesets, props)
        if new_props != props:
            topo.replace(face, new_props)
            styled += 1
    return styled
