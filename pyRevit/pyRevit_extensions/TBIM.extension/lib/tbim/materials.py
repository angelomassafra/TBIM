"""Material library of TBIM: construction materials and layered constructions (U-values).

A construction is a list of layers ``(material, thickness in mm)`` from the outside (or the top) to the
inside (or the bottom), the order of the layers of a Revit compound structure. In the Informational Rule
Sets it is the text of ``stFC_Layers``, e.g. ``"Clay roof tiles 20 mm / Timber battens 40 mm"``.

    MATERIALS[name] = (RGB colour, thermal conductivity W/(m K), density kg/m3, specific heat J/(kg K),
                       Revit layer function, transparency %)
"""
import re

STRUCTURE, SUBSTRATE, INSULATION, FINISH1, FINISH2 = "Structure", "Substrate", "Insulation", "Finish1", "Finish2"
FUNCTIONS = [STRUCTURE, SUBSTRATE, INSULATION, FINISH1, FINISH2]  # Revit priority order

MATERIALS = {
    # renders, plasters, finishes
    "Lime plaster": ((238, 232, 218), 0.70, 1600, 1000, FINISH2, 0),
    "Lime-cement plaster": ((236, 233, 226), 0.90, 1800, 1000, FINISH2, 0),
    "Whitewashed lime render": ((248, 247, 240), 0.70, 1600, 1000, FINISH1, 0),
    "Ochre lime render": ((222, 183, 112), 0.80, 1700, 1000, FINISH1, 0),
    "Rusticated lime render": ((214, 176, 108), 0.80, 1700, 1000, FINISH1, 0),
    "Cream cement render": ((232, 222, 196), 0.90, 1800, 1000, FINISH1, 0),
    "Gypsum board": ((242, 242, 238), 0.25, 900, 1000, FINISH2, 0),
    "Fire-rated gypsum board": ((236, 226, 226), 0.25, 950, 1000, FINISH2, 0),
    "Mineral fibre ceiling tiles": ((246, 246, 244), 0.06, 300, 840, FINISH2, 0),
    "Reed-and-plaster ceiling": ((232, 226, 210), 0.30, 900, 1000, FINISH2, 0),
    # floor finishes and screeds
    "Venetian terrazzo": ((206, 196, 182), 1.50, 2300, 1000, FINISH1, 0),
    "Marble-chip terrazzo tiles": ((214, 208, 196), 1.50, 2300, 1000, FINISH1, 0),
    "Porcelain stoneware tiles": ((196, 190, 180), 1.30, 2300, 840, FINISH1, 0),
    "Natural stone tiles": ((190, 184, 172), 2.30, 2600, 840, FINISH1, 0),
    "Linoleum": ((168, 120, 92), 0.17, 1200, 1400, FINISH1, 0),
    "Limestone paving slabs": ((222, 212, 186), 1.70, 2400, 840, FINISH1, 0),
    "Timber floorboards": ((176, 128, 80), 0.13, 500, 1600, FINISH1, 0),
    "Raised access floor panel": ((150, 150, 152), 0.40, 1500, 1000, FINISH1, 0),
    "Cement screed": ((198, 194, 186), 1.40, 2000, 1000, SUBSTRATE, 0),
    "Lime screed": ((214, 206, 188), 0.90, 1800, 1000, SUBSTRATE, 0),
    "Lightweight concrete screed": ((200, 198, 192), 0.40, 1000, 1000, SUBSTRATE, 0),
    "Cement mortar bed": ((190, 186, 178), 1.40, 2000, 1000, SUBSTRATE, 0),
    "Lime mortar bed": ((214, 208, 192), 0.90, 1800, 1000, SUBSTRATE, 0),
    # roof coverings
    "Clay roof tiles": ((176, 84, 54), 1.00, 2000, 800, FINISH1, 0),
    "Lead sheet": ((104, 110, 118), 35.0, 11300, 130, FINISH1, 0),
    "Bitumen membrane": ((52, 52, 56), 0.17, 1100, 1000, SUBSTRATE, 0),
    "Gravel ballast": ((178, 172, 160), 2.00, 1800, 1000, FINISH1, 0),
    "Standing-seam aluminium sheet": ((176, 182, 188), 160.0, 2700, 880, FINISH1, 0),
    "Pre-painted corrugated steel sheet": ((78, 84, 92), 50.0, 7800, 450, FINISH1, 0),
    "Lime-tuff roof screed": ((232, 224, 200), 0.80, 1600, 1000, FINISH1, 0),
    # masonry and concrete
    "Solid clay brick": ((178, 96, 66), 0.72, 1800, 840, STRUCTURE, 0),
    "Exposed solid brick": ((166, 76, 52), 0.80, 1850, 840, FINISH1, 0),
    "Facing brick": ((158, 74, 50), 0.90, 1900, 840, FINISH1, 0),
    "Hollow clay brick": ((198, 122, 86), 0.36, 800, 840, STRUCTURE, 0),
    "Perforated clay brick": ((192, 112, 78), 0.30, 850, 840, STRUCTURE, 0),
    "Clay-concrete slab": ((202, 150, 120), 0.66, 1100, 900, STRUCTURE, 0),
    "Solid brick jack-arch slab": ((184, 104, 72), 0.80, 1700, 840, STRUCTURE, 0),
    "Tuff ashlar": ((222, 196, 140), 0.63, 1500, 900, STRUCTURE, 0),
    "Exposed tuff ashlar": ((214, 184, 120), 0.63, 1500, 900, FINISH1, 0),
    "Tuff stone vault": ((220, 194, 140), 0.63, 1500, 900, STRUCTURE, 0),
    "Tuff rubble fill": ((206, 186, 150), 0.40, 1200, 900, SUBSTRATE, 0),
    "Limestone ashlar": ((228, 220, 196), 1.70, 2400, 840, FINISH1, 0),
    "Reinforced concrete": ((168, 168, 164), 2.30, 2400, 1000, STRUCTURE, 0),
    "Precast concrete": ((206, 202, 192), 2.00, 2300, 1000, STRUCTURE, 0),
    "Precast hollow-core slab": ((196, 194, 188), 1.20, 1600, 1000, STRUCTURE, 0),
    "Lean concrete": ((180, 176, 168), 1.30, 2000, 1000, SUBSTRATE, 0),
    "Gravel fill": ((150, 144, 134), 2.00, 1800, 1000, SUBSTRATE, 0),
    "Compacted earth": ((128, 104, 78), 1.50, 1800, 1000, SUBSTRATE, 0),
    # timber and metals
    "Timber battens": ((170, 124, 78), 0.13, 500, 1600, SUBSTRATE, 0),
    "Timber boarding": ((184, 140, 92), 0.13, 500, 1600, SUBSTRATE, 0),
    "Timber rafters": ((150, 104, 64), 0.13, 500, 1600, STRUCTURE, 0),
    "Timber beams": ((140, 96, 58), 0.13, 500, 1600, STRUCTURE, 0),
    "Steel trusses": ((96, 104, 114), 50.0, 7800, 450, STRUCTURE, 0),
    "Aluminium composite panel": ((186, 190, 196), 0.50, 1400, 900, FINISH1, 0),
    "Aluminium louvres": ((150, 156, 162), 160.0, 2700, 880, FINISH1, 0),
    "Terracotta rainscreen tiles": ((190, 98, 62), 1.00, 2000, 800, FINISH1, 0),
    # insulation and air layers
    "EPS insulation": ((238, 238, 236), 0.035, 20, 1450, INSULATION, 0),
    "XPS insulation": ((150, 196, 230), 0.034, 35, 1450, INSULATION, 0),
    "Mineral wool": ((232, 206, 112), 0.035, 40, 1030, INSULATION, 0),
    "Cork insulation": ((150, 104, 66), 0.045, 120, 1800, INSULATION, 0),
    "Air cavity": ((250, 250, 250), 0.33, 1.2, 1000, INSULATION, 0),     # 60 mm still air: R 0.18
    "Ventilated air cavity": ((250, 250, 250), 2.0, 1.2, 1000, INSULATION, 0),  # not counted
    "Floor void": ((250, 250, 250), 0.50, 1.2, 1000, INSULATION, 0),
    # glazing
    "Triple glazing unit": ((84, 128, 150), 0.05, 2500, 750, FINISH1, 45),
    "Insulated spandrel panel": ((52, 60, 70), 0.04, 200, 1000, INSULATION, 0),
    "Laminated double glazing": ((150, 194, 210), 0.07, 2500, 750, FINISH1, 55),
    "Laminated safety glass": ((170, 208, 220), 1.00, 2500, 750, FINISH1, 60),
}

# surface resistances (m2 K/W): (inside, outside) by face type, EN ISO 6946
SURFACE = {"extVer": (0.13, 0.04), "intVer": (0.13, 0.13), "topHor": (0.10, 0.04), "extInc": (0.10, 0.04),
           "botHor": (0.17, 0.04), "intHor": (0.10, 0.10)}
_LAYER = re.compile(r"^(.+?)\s+(\d+(?:\.\d+)?)\s*mm$")


def text(layers):
    """``[("Clay roof tiles", 20), ...]`` -> ``"Clay roof tiles 20 mm / ..."``."""
    for name, _ in layers:
        if name not in MATERIALS:
            raise KeyError("Unknown material: %s" % name)
    return " / ".join("%s %g mm" % (name, mm) for name, mm in layers)


def parse(layers_text):
    """Inverse of :func:`text`."""
    out = []
    for item in layers_text.split(" / "):
        m = _LAYER.match(item.strip())
        if m is None or m.group(1) not in MATERIALS:
            raise ValueError("Not a layer of a known material: %r" % item)
        out.append((m.group(1), float(m.group(2))))
    return out


def thickness(layers):
    return sum(mm for _, mm in layers)


def u_value(layers, face_type):
    """Thermal transmittance (W/(m2 K)) of the layers, rounded to 0.01."""
    rsi, rse = SURFACE.get(face_type, (0.13, 0.04))
    r = rsi + rse + sum(mm / 1000.0 / MATERIALS[name][1] for name, mm in layers if name != "Ventilated air cavity")
    return round(1.0 / r, 2)


def shell_functions(functions):
    """Layer functions valid for a Revit compound structure. Return (functions, first core layer, last core layer).

    The core spans the structure layers (all the layers if there is none); in the shells (outside and inside the
    core) the function priority may not decrease from the core outwards, so a lower one is raised: e.g. timber
    battens (substrate) outside the insulation become insulation-priority layers.
    """
    functions = list(functions)
    structure = [i for i, f in enumerate(functions) if f == STRUCTURE]
    first, last = (structure[0], structure[-1]) if structure else (0, len(functions) - 1)
    for indices in (range(first - 1, -1, -1), range(last + 1, len(functions))):
        running = 0
        for i in indices:
            running = max(running, FUNCTIONS.index(functions[i]))
            functions[i] = FUNCTIONS[running]
    return functions, first, last


def revit_spec(layers):
    """Layers for the Revit side: ``name:mm:function:r,g,b:transparency:conductivity:density:specific heat``."""
    out = []
    for name, mm in layers:
        rgb, k, rho, c, function, transparency = MATERIALS[name]
        out.append("%s:%g:%s:%d,%d,%d:%d:%g:%g:%g" % ((name, mm, function) + tuple(rgb) + (transparency, k, rho, c)))
    return ";".join(out)
