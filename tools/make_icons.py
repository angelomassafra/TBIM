"""Draw the ribbon icons of the TBIM commands in the TBIM style.

Style: 96x96 px, flat circle in the color of the panel, white line glyph
(6 px strokes with round ends). Only the icons listed in ICONS are (re)drawn;
the other icons of the extension already follow this style.

    python tools/make_icons.py          # needs Pillow
    python tools/make_icons.py TBEM     # the icons of the TBEM tab
"""
import os
import sys

from PIL import Image, ImageDraw

SIZE, SCALE = 96, 4
S = SIZE * SCALE
STROKE = 6 * SCALE
WHITE = (255, 255, 255, 255)
EXTENSION = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                         "pyRevit", "pyRevit_extensions", "TBIM.extension")
TAB = os.path.join(EXTENSION, "TBIM.tab")

PANEL_COLORS = {
    "Project": (142, 108, 199),
    "InstanceBIM": (255, 211, 36),
    "Visualize": (31, 163, 163),
    "Export": (214, 96, 77),
    "Loads": (239, 120, 69),
    "TopologicalBIM": (180, 90, 160),
    # TBEM tab
    "Spatial BEM": (52, 140, 210),
    "Topological BEM": (120, 84, 190),
    "Full TBEM": (214, 120, 40),
    "Energy Simulation": (40, 160, 90),
}


def p(x, y):
    """Glyph coordinates on a 0-96 grid -> supersampled pixels."""
    return (x * SCALE, y * SCALE)


def line(d, *points, width=STROKE):
    pts = [p(*q) for q in points]
    d.line(pts, fill=WHITE, width=width, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=WHITE)


def rect(d, x0, y0, x1, y1):
    line(d, (x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))


def dot(d, x, y, r):
    d.ellipse([p(x - r, y - r), p(x + r, y + r)], fill=WHITE)


def ring(d, x, y, r):
    d.ellipse([p(x - r, y - r), p(x + r, y + r)], outline=WHITE, width=STROKE)


def folder(d, plus=False, open_=False):
    line(d, (24, 34), (24, 68), (72, 68), (72, 38), (48, 38), (42, 30), (24, 30), (24, 34))
    if open_:
        line(d, (24, 68), (32, 48), (80, 48), (72, 68))
    if plus:
        line(d, (48, 46), (48, 60))
        line(d, (41, 53), (55, 53))


# --------------------------------------------------------------------------------------
# Glyphs
def g_new(d):
    folder(d, plus=True)


def g_open(d):
    folder(d, open_=True)


def g_info(d):
    dot(d, 48, 30, 4.5)
    line(d, (48, 42), (48, 66))
    line(d, (41, 42), (48, 42))
    line(d, (41, 66), (55, 66))


def g_folder(d):
    folder(d)


def g_model(d):
    # isometric cube
    line(d, (48, 24), (70, 34), (70, 60), (48, 72), (26, 60), (26, 34), (48, 24))
    line(d, (26, 34), (48, 46), (70, 34))
    line(d, (48, 46), (48, 72))


def g_graph(d):
    nodes = [(30, 30), (66, 28), (28, 66), (68, 64), (48, 48)]
    for a, b in ((0, 4), (1, 4), (2, 4), (3, 4), (0, 1), (2, 3)):
        line(d, nodes[a], nodes[b], width=4 * SCALE)
    for x, y in nodes:
        dot(d, x, y, 7)


def g_passage_graph(d):
    # two rooms, a node in each, linked through the door in the wall between them
    line(d, (14, 26), (82, 26), (82, 70), (14, 70), (14, 26))
    line(d, (48, 26), (48, 38))
    line(d, (48, 58), (48, 70))
    line(d, (31, 48), (65, 48), width=4 * SCALE)
    dot(d, 31, 48, 7)
    dot(d, 65, 48, 7)


def g_types(d):
    # three stacked layers (element types)
    for y in (32, 48, 64):
        line(d, (24, y), (48, y - 10), (72, y), (48, y + 10), (24, y))


def g_data(d):
    line(d, (24, 72), (72, 72))
    for x, h in ((32, 18), (48, 34), (64, 26)):
        d.rectangle([p(x - 5, 72 - h - 4), p(x + 5, 68)], fill=WHITE)


def g_clear(d):
    # eraser
    line(d, (30, 58), (54, 34), (70, 50), (46, 74), (38, 74), (30, 66), (30, 58))
    line(d, (42, 46), (58, 62))
    line(d, (46, 74), (72, 74))


def g_move_apertures(d):
    rect(d, 36, 30, 60, 66)
    line(d, (48, 30), (48, 66), width=4 * SCALE)
    line(d, (16, 48), (28, 48))
    line(d, (22, 42), (16, 48), (22, 54))
    line(d, (68, 48), (80, 48))
    line(d, (74, 42), (80, 48), (74, 54))


def g_by_occupancy_type(d):
    ring(d, 48, 34, 9)
    d.arc([p(26, 50), p(70, 94)], 180, 360, fill=WHITE, width=STROKE)
    line(d, (26, 72), (70, 72))


def g_by_table_of_spaces(d):
    rect(d, 24, 28, 72, 68)
    line(d, (24, 41), (72, 41))
    line(d, (24, 55), (72, 55))
    line(d, (40, 28), (40, 68))


def g_by_model(d):
    rect(d, 30, 34, 66, 70)
    line(d, (30, 24), (66, 24))
    line(d, (30, 20), (30, 28))
    line(d, (66, 20), (66, 28))
    line(d, (76, 34), (76, 70))
    line(d, (72, 34), (80, 34))
    line(d, (72, 70), (80, 70))


def building(d):
    line(d, (26, 72), (26, 40), (48, 26), (70, 40), (70, 72), (26, 72))


def g_revit(d):
    building(d)
    rect(d, 36, 50, 44, 58)
    rect(d, 52, 50, 60, 58)


def g_update_data(d):
    building(d)
    line(d, (48, 40), (48, 64))
    line(d, (40, 56), (48, 64), (56, 56))


def export_arrow(d):
    line(d, (48, 20), (48, 46))
    line(d, (39, 37), (48, 46), (57, 37))


def g_ifc(d):
    export_arrow(d)
    line(d, (24, 56), (24, 74), (72, 74), (72, 56))
    for x in (34, 48, 62):
        dot(d, x, 63, 4)


def g_topologic(d):
    export_arrow(d)
    line(d, (24, 56), (24, 74), (72, 74), (72, 56))
    line(d, (34, 64), (48, 58), (62, 64))
    dot(d, 34, 64, 4)
    dot(d, 48, 58, 4)
    dot(d, 62, 64, 4)


def g_run(d):
    line(d, (36, 28), (36, 68), (70, 48), (36, 28))


def g_check_model(d):
    building(d)
    line(d, (38, 54), (46, 62), (60, 46))


def g_from_table(d):
    rect(d, 22, 26, 74, 70)
    line(d, (22, 41), (74, 41))
    line(d, (22, 55), (74, 55))
    line(d, (42, 26), (42, 70))


def g_by_rules(d):
    rect(d, 20, 28, 44, 52)
    line(d, (32, 28), (32, 52))
    line(d, (20, 40), (44, 40))
    line(d, (54, 70), (54, 30), (76, 30), (76, 70))
    dot(d, 70, 52, 3)


ICONS = {
    "Project.Panel/New.pushbutton": ("Project", g_new),
    "Project.Panel/Open.pushbutton": ("Project", g_open),
    "Project.Panel/Run.pushbutton": ("Project", g_run),
    "Project.Panel/CheckModel.pushbutton": ("Project", g_check_model),
    "Project.Panel/Info.pushbutton": ("Project", g_info),
    "Loads.Panel/Assignment.pulldown/FromTable.pushbutton": ("Loads", g_from_table),
    "TopologicalBIM.Panel/ByRules.pushbutton": ("TopologicalBIM", g_by_rules),
    "Project.Panel/Folder.pushbutton": ("Project", g_folder),
    "Visualize.Panel/Model.pushbutton": ("Visualize", g_model),
    "Visualize.Panel/DualGraph.pushbutton": ("Visualize", g_graph),
    "Visualize.Panel/PassageGraph.pushbutton": ("Visualize", g_passage_graph),
    "Visualize.Panel/Types.pushbutton": ("Visualize", g_types),
    "Visualize.Panel/Data.pushbutton": ("Visualize", g_data),
    "Visualize.Panel/Clear.pushbutton": ("Visualize", g_clear),
    "InstanceBIM.Panel/CellComplex.pulldown/MoveApertures.pushbutton": ("InstanceBIM", g_move_apertures),
    "InstanceBIM.Panel/CellComplex.pulldown/ByOccupancyType.pushbutton": ("InstanceBIM", g_by_occupancy_type),
    "InstanceBIM.Panel/CellComplex.pulldown/ByTableOfSpaces.pushbutton": ("InstanceBIM", g_by_table_of_spaces),
    "InstanceBIM.Panel/CellComplex.pulldown/ByModel.pushbutton": ("InstanceBIM", g_by_model),
    "InstanceBIM.Panel/Revit.pulldown": ("InstanceBIM", g_revit),
    "InstanceBIM.Panel/Revit.pulldown/UpdateData.pushbutton": ("InstanceBIM", g_update_data),
    "Export.Panel/IFC.pushbutton": ("Export", g_ifc),
    "Export.Panel/Topologic.pushbutton": ("Export", g_topologic),
}


# --------------------------------------------------------------------------------------
# Glyphs of the TBEM tab
def g_zones(d):
    rect(d, 20, 26, 76, 70)
    line(d, (46, 26), (46, 70))
    line(d, (46, 48), (76, 48))


def g_clusterize(d):
    for cx, cy in ((32, 34), (64, 36), (46, 64)):
        for dx, dy in ((-6, -4), (6, -2), (0, 6)):
            dot(d, cx + dx, cy + dy, 4)


def g_from_tbim(d):
    building(d)
    line(d, (38, 60), (48, 50), (58, 60))
    line(d, (48, 50), (48, 68))


def g_merge(d):
    rect(d, 18, 34, 38, 62)
    rect(d, 58, 34, 78, 62)
    line(d, (40, 48), (56, 48))
    line(d, (44, 42), (40, 48), (44, 54))
    line(d, (52, 42), (56, 48), (52, 54))


def g_exclude(d):
    rect(d, 24, 28, 72, 68)
    line(d, (36, 40), (60, 56))
    line(d, (60, 40), (36, 56))


def g_include(d):
    rect(d, 24, 28, 72, 68)
    line(d, (48, 36), (48, 60))
    line(d, (36, 48), (60, 48))


def g_show(d):
    d.arc([p(16, 30), p(80, 82)], 200, 340, fill=WHITE, width=STROKE)
    d.arc([p(16, 14), p(80, 66)], 20, 160, fill=WHITE, width=STROKE)
    dot(d, 48, 48, 8)


def g_edit(d):
    line(d, (30, 66), (62, 34), (70, 42), (38, 74), (28, 76), (30, 66))
    line(d, (56, 40), (64, 48))


def g_schedules(d):
    ring(d, 48, 48, 24)
    line(d, (48, 34), (48, 48), (58, 54))


def g_import(d):
    line(d, (48, 18), (48, 44))
    line(d, (39, 35), (48, 44), (57, 35))
    line(d, (24, 54), (24, 74), (72, 74), (72, 54))


def g_check(d):
    rect(d, 24, 26, 72, 70)
    line(d, (34, 48), (44, 58), (62, 38))


def g_build_topological(d):
    g_model(d)
    for x, y in ((48, 24), (70, 34), (70, 60), (48, 72), (26, 60), (26, 34), (48, 46)):
        dot(d, x, y, 5)


def g_build_full(d):
    g_model(d)
    line(d, (30, 44), (44, 51))
    line(d, (30, 53), (44, 60))


def g_boundaries(d):
    line(d, (40, 22), (40, 74))
    line(d, (56, 22), (56, 74))
    line(d, (64, 40), (78, 40))
    line(d, (64, 56), (78, 56))
    line(d, (18, 48), (32, 48))


def g_adiabatic(d):
    line(d, (40, 22), (40, 74))
    line(d, (56, 22), (56, 74))
    for y in (32, 46, 60):
        line(d, (40, y + 8), (56, y), width=4 * SCALE)


def g_ground(d):
    line(d, (18, 44), (78, 44))
    for x in (30, 44, 58, 72):
        line(d, (x, 52), (x - 8, 64), width=4 * SCALE)
    line(d, (48, 20), (48, 36))


def rays(d, width=4 * SCALE):
    for a, b in (((48, 20), (48, 28)), ((48, 68), (48, 76)), ((20, 48), (28, 48)), ((68, 48), (76, 48)),
                 ((28, 28), (34, 34)), ((62, 62), (68, 68)), ((28, 68), (34, 62)), ((62, 34), (68, 28))):
        line(d, a, b, width=width)


def g_outdoors(d):
    ring(d, 48, 48, 12)
    rays(d)


def g_reset(d):
    d.arc([p(24, 24), p(72, 72)], 40, 320, fill=WHITE, width=STROKE)
    line(d, (66, 22), (68, 36), (54, 36))


def g_constructions(d):
    for y in (28, 42, 56, 70):
        line(d, (24, y), (72, y))
    line(d, (24, 28), (24, 70))
    line(d, (72, 28), (72, 70))


def g_shading(d):
    ring(d, 30, 32, 9)
    for y in (48, 60, 72):
        line(d, (44, y - 8), (78, y))


def g_infiltration(d):
    line(d, (20, 36), (60, 36))
    d.arc([p(52, 22), p(72, 42)], 270, 90, fill=WHITE, width=STROKE)
    line(d, (20, 52), (72, 52))
    line(d, (20, 66), (52, 66))
    d.arc([p(44, 58), p(60, 74)], 270, 90, fill=WHITE, width=STROKE)


def g_weather(d):
    ring(d, 38, 38, 12)
    d.arc([p(36, 44), p(60, 68)], 180, 360, fill=WHITE, width=STROKE)
    d.arc([p(52, 40), p(76, 64)], 240, 360, fill=WHITE, width=STROKE)
    line(d, (30, 68), (76, 68))
    d.arc([p(24, 56), p(36, 68)], 90, 270, fill=WHITE, width=STROKE)


def g_settings(d):
    # sliders
    for y, x in ((30, 36), (48, 60), (66, 42)):
        line(d, (22, y), (74, y))
        dot(d, x, y, 7)


def g_idf(d):
    line(d, (30, 20), (58, 20), (68, 30), (68, 76), (30, 76), (30, 20))
    line(d, (40, 38), (58, 38))
    line(d, (40, 50), (58, 50))
    line(d, (40, 62), (52, 62))


def g_map(d):
    rect(d, 20, 26, 76, 70)
    d.rectangle([p(24, 30), p(44, 46)], fill=WHITE)
    d.rectangle([p(52, 50), p(72, 66)], fill=WHITE)


def g_charts(d):
    line(d, (22, 20), (22, 74), (76, 74))
    for x0, top in ((30, 52), (46, 34), (62, 44)):
        d.rectangle([p(x0, top), p(x0 + 10, 70)], fill=WHITE)


def g_map_3d(d):
    # a block with a filled top
    top = [p(48, 18), p(76, 32), p(48, 46), p(20, 32)]
    d.polygon(top, fill=WHITE)
    line(d, (20, 32), (20, 62), (48, 76), (76, 62), (76, 32))
    line(d, (48, 46), (48, 76))


TBEM_ICONS = {
    "Project.Panel/New.pushbutton": ("Project", g_new),
    "Project.Panel/Open.pushbutton": ("Project", g_open),
    "Project.Panel/Run.pushbutton": ("Project", g_run),
    "Project.Panel/CheckModel.pushbutton": ("Project", g_check_model),
    "Project.Panel/Info.pushbutton": ("Project", g_info),
    "Project.Panel/Folder.pushbutton": ("Project", g_folder),
    "Spatial BEM.Panel/Zones.pulldown": ("Spatial BEM", g_zones),
    "Spatial BEM.Panel/Zones.pulldown/Clusterize.pushbutton": ("Spatial BEM", g_clusterize),
    "Spatial BEM.Panel/Zones.pulldown/FromTBIM.pushbutton": ("Spatial BEM", g_from_tbim),
    "Spatial BEM.Panel/Zones.pulldown/Merge.pushbutton": ("Spatial BEM", g_merge),
    "Spatial BEM.Panel/Zones.pulldown/Exclude.pushbutton": ("Spatial BEM", g_exclude),
    "Spatial BEM.Panel/Zones.pulldown/Include.pushbutton": ("Spatial BEM", g_include),
    "Spatial BEM.Panel/Programs.pulldown": ("Spatial BEM", g_by_occupancy_type),
    "Spatial BEM.Panel/Programs.pulldown/Check.pushbutton": ("Spatial BEM", g_check),
    "Spatial BEM.Panel/Programs.pulldown/Edit.pushbutton": ("Spatial BEM", g_edit),
    "Spatial BEM.Panel/Schedules.pulldown": ("Spatial BEM", g_schedules),
    "Spatial BEM.Panel/Schedules.pulldown/Import.pushbutton": ("Spatial BEM", g_import),
    "Spatial BEM.Panel/Schedules.pulldown/Check.pushbutton": ("Spatial BEM", g_check),
    "Spatial BEM.Panel/Build.pushbutton": ("Spatial BEM", g_model),
    "Topological BEM.Panel/Boundaries.pulldown": ("Topological BEM", g_boundaries),
    "Topological BEM.Panel/Boundaries.pulldown/Adiabatic.pushbutton": ("Topological BEM", g_adiabatic),
    "Topological BEM.Panel/Boundaries.pulldown/Ground.pushbutton": ("Topological BEM", g_ground),
    "Topological BEM.Panel/Boundaries.pulldown/Outdoors.pushbutton": ("Topological BEM", g_outdoors),
    "Topological BEM.Panel/Boundaries.pulldown/Reset.pushbutton": ("Topological BEM", g_reset),
    "Topological BEM.Panel/Build.pushbutton": ("Topological BEM", g_build_topological),
    "Full TBEM.Panel/Constructions.pushbutton": ("Full TBEM", g_constructions),
    "Full TBEM.Panel/Shading.pulldown": ("Full TBEM", g_shading),
    "Full TBEM.Panel/Shading.pulldown/Import.pushbutton": ("Full TBEM", g_import),
    "Full TBEM.Panel/Shading.pulldown/Clear.pushbutton": ("Full TBEM", g_clear),
    "Full TBEM.Panel/Infiltration.pushbutton": ("Full TBEM", g_infiltration),
    "Full TBEM.Panel/Build.pushbutton": ("Full TBEM", g_build_full),
    "Energy Simulation.Panel/Weather.pushbutton": ("Energy Simulation", g_weather),
    "Energy Simulation.Panel/Settings.pushbutton": ("Energy Simulation", g_settings),
    "Energy Simulation.Panel/IDF.pushbutton": ("Energy Simulation", g_idf),
    "Energy Simulation.Panel/Run.pushbutton": ("Energy Simulation", g_run),
    "Energy Simulation.Panel/Results.pulldown": ("Energy Simulation", g_data),
    "Energy Simulation.Panel/Results.pulldown/Summary.pushbutton": ("Energy Simulation", g_data),
    "Energy Simulation.Panel/Results.pulldown/WriteToSpaces.pushbutton": ("Energy Simulation", g_update_data),
    "Visualize.Panel/Zones.pulldown": ("Visualize", g_zones),
    "Visualize.Panel/Zones.pulldown/Map3D.pushbutton": ("Visualize", g_map_3d),
    "Visualize.Panel/Zones.pulldown/Map2D.pushbutton": ("Visualize", g_map),
    "Visualize.Panel/Boundaries.pushbutton": ("Visualize", g_boundaries),
    "Visualize.Panel/Charts.pushbutton": ("Visualize", g_charts),
    "Visualize.Panel/Map3D.pushbutton": ("Visualize", g_map_3d),
    "Visualize.Panel/Map2D.pushbutton": ("Visualize", g_map),
    "Visualize.Panel/Clear.pushbutton": ("Visualize", g_clear),
}


def draw(color, glyph):
    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse([0, 0, S - 1, S - 1], fill=color + (255,))
    glyph(d)
    return image.resize((SIZE, SIZE), Image.LANCZOS)


def main(tab="TBIM"):
    icons = TBEM_ICONS if tab == "TBEM" else ICONS
    root = os.path.join(EXTENSION, "%s.tab" % tab)
    for folder, (panel, glyph) in sorted(icons.items()):
        path = os.path.join(root, folder, "icon.png")
        draw(PANEL_COLORS[panel], glyph).save(path)
        print("icon:", os.path.relpath(path, root))


if __name__ == "__main__":
    main(*sys.argv[1:2])
