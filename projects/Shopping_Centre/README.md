# Shopping Centre - TBIM example project

An invented two-level shopping centre: an 80 m long double-height glazed gallery with two levels of shops on both sides, a food court on the upper level, a two-level department store at the east end, an entrance hall at the west end and two plant rooms on the roof. Precast structure, insulated metal panels.

![The Shopping Centre in Revit, at the end of the TBIM workflow](img/model.png)

The building was generated and run through the complete TBIM workflow automatically: it is one of the six
buildings of the [six-building video](../../docs/video/tbim_six_buildings.mp4).

## Model

| | |
|---|---|
| Cells (rooms) | 37 |
| Building storeys | 4 |
| Revit | 119 walls, 40 floors, 22 roofs, 37 spaces, 41 windows, 35 doors |
| Thermal zones | 10 |
| Occupancy types | Retail:Shop, Retail:DepartmentStore, Food:FoodCourt, Circulation:Gallery, Circulation:EntranceHall, Technical:Plant |

## Files

| | |
|---|---|
| `make_model.py` | Floor plans (rooms as boxes), ILDs, InstanceBIM data, IRSs and window/door rules: writes `3d/` and `json/` |
| `3d/*.brep` | Massing model, one CellComplex per building block (centimetres) |
| `json/` | TBIM data of every step of the workflow |
| `Shopping_Centre.rvt` | Revit 2026 model at the end of the workflow, with the TBIM views and legends |
| `export/Shopping_Centre.ifc` | IFC4 Reference View with the TBIM property sets (Export > IFC) |
| `export/tbim_InstanceBIM.*` | InstanceBIM as topologicpy JSON, BREP, OBJ and dual graph JSON (Export > Topologic) |

## Rebuild

```bat
python make_model.py
```

then follow the [tutorial](../../docs/USER_MANUAL.md#4-tutorial-the-demo-school-step-by-step) on an empty Revit model
(**Project > Open** this folder). Windows and doors come from a stand-in of the TopologicalBIM panel:
`python tools/topologicalbim_standin.py projects/Shopping_Centre` (see [tools](../../tools)).
