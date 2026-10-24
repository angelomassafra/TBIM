# Town Hall - TBIM example project

An invented early-20th-century town hall: a 40 x 18 m plan with offices on both sides of a central block (entrance hall on the ground floor, a double-height council chamber above it), corridors along the back, a hipped clay-tile roof and a clock tower with a belfry on the front. Brick masonry, steel-beam and brick-vault slabs.

![The Town Hall in Revit, at the end of the TBIM workflow](img/model.png)

The building was generated and run through the complete TBIM workflow automatically: it is one of the six
buildings of the [six-building video](../../docs/video/tbim_six_buildings.mp4).

## Model

| | |
|---|---|
| Cells (rooms) | 35 |
| Building storeys | 6 |
| Revit | 111 walls, 45 floors, 5 roofs, 35 spaces, 51 windows, 31 doors |
| Thermal zones | 22 |
| Occupancy types | Office:PublicDesk, Office:Registry, Office:Private, Office:Administration, Archive:Records, Circulation:Corridor, Circulation:EntranceHall, Assembly:CouncilChamber, Unconditioned:Attic, Civic:ClockTower, Civic:Belfry |

## Files

| | |
|---|---|
| `make_model.py` | Floor plans (rooms as boxes), ILDs, InstanceBIM data, IRSs and window/door rules: writes `3d/` and `json/` |
| `3d/*.brep` | Massing model, one CellComplex per building block (centimetres) |
| `json/` | TBIM data of every step of the workflow |
| `Town_Hall.rvt` | Revit 2026 model at the end of the workflow, with the TBIM views and legends |
| `export/Town_Hall.ifc` | IFC4 Reference View with the TBIM property sets (Export > IFC) |
| `export/tbim_InstanceBIM.*` | InstanceBIM as topologicpy JSON, BREP, OBJ and dual graph JSON (Export > Topologic) |

## Rebuild

```bat
python make_model.py
```

then follow the [tutorial](../../docs/USER_MANUAL.md#4-tutorial-the-demo-school-step-by-step) on an empty Revit model
(**Project > Open** this folder). Windows and doors come from a stand-in of the TopologicalBIM panel:
`python tools/topologicalbim_standin.py projects/Town_Hall` (see [tools](../../tools)).
