# School - TBIM example project

An invented two-storey school of the late 1970s: an L-shaped plan with a classroom wing (classrooms facing south along a corridor, stair and toilets behind it, entrance hall and administration on the ground floor, library and science lab upstairs) and a single-storey gym with changing rooms under a steel gable roof.

![The School in Revit, at the end of the TBIM workflow](img/model.png)

The building was generated and run through the complete TBIM workflow automatically: it is one of the six
buildings of the [six-building video](../../docs/video/tbim_six_buildings.mp4).

## Model

| | |
|---|---|
| Cells (rooms) | 23 |
| Building storeys | 4 |
| Revit | 74 walls, 23 floors, 14 roofs, 23 spaces, 29 windows, 25 doors |
| Thermal zones | 17 |
| Occupancy types | Education:Classroom, Education:Library, Education:Laboratory, Office:Administration, Circulation:EntranceHall, Circulation:Corridor, Circulation:Stair, Support:Restroom, Sports:Gym, Support:ChangingRoom, Storage:Equipment, Unconditioned:Attic |

## Files

| | |
|---|---|
| `make_model.py` | Floor plans (rooms as boxes), ILDs, InstanceBIM data, IRSs and window/door rules: writes `3d/` and `json/` |
| `3d/*.brep` | Massing model, one CellComplex per building block (centimetres) |
| `json/` | TBIM data of every step of the workflow |
| `School.rvt` | Revit 2026 model at the end of the workflow, with the TBIM views and legends |
| `export/School.ifc` | IFC4 Reference View with the TBIM property sets (Export > IFC) |
| `export/tbim_InstanceBIM.*` | InstanceBIM as topologicpy JSON, BREP, OBJ and dual graph JSON (Export > Topologic) |

## Rebuild

```bat
python make_model.py
```

then follow the [tutorial](../../docs/USER_MANUAL.md#4-tutorial-the-demo-school-step-by-step) on an empty Revit model
(**Project > Open** this folder). Windows and doors come from a stand-in of the TopologicalBIM panel:
`python tools/topologicalbim_standin.py projects/School` (see [tools](../../tools)).
