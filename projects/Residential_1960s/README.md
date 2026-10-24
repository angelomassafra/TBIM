# Residential 1960s - TBIM case study

An existing multi-storey residential building of the mid 1960s in northern Italy, modelled with TBIM from the
archive drawings of its building permit (plans 1:100, elevations, section). The case study is **anonymized**:
address, owners, designers and permit references are omitted, and the model is a simplified reconstruction.

![The TBIM model](img/06_ibim_3d.png)

![The TBIM workflow on the case study](video/tbim_residential_1960s.gif)

Video: [video/tbim_residential_1960s.mp4](video/tbim_residential_1960s.mp4)

## Model

| | |
|---|---|
| Footprint | 22.00 x 14.30 m, two flats per storey beside the central stair and lift |
| Storeys | basement (garages, boiler room) z 0-2.80 m; 5 residential storeys of 3.00 m (raised floor + 4 typical) |
| Roof | hipped, clay tiles, 30 % slope, attic not heated; stair turret up to z 20.80 m |
| Project North | 131 degrees |
| Cells | 112: 5 basement, 105 rooms (21 per storey, from the typical plan), attic, turret |
| Revit | 334 walls, 138 slabs, 5 roofs (4 pitches + turret), 112 spaces, 99 windows, 91 doors |

Construction (typical of Italian 1960s condominiums), as Informational Rule Sets with U-values (W/m2K):

| Element | Type | U |
|---|---|---|
| External walls | RC frame, cavity wall: facing brick 12 / air 6 / hollow brick 8 / plaster | 1.10 |
| Basement walls | RC 30 against the ground | 2.20 |
| Slabs | clay-concrete (laterocemento) 20+4 | 1.60 |
| Slab under the attic | clay-concrete 20+4 | 1.70 |
| Roof | clay tiles on inclined clay-concrete slab | 1.80 |
| Windows | anodized aluminium, single glazing 4 mm | 5.80 |

## Files

- `make_model.py`: BReps of the three blocks (Seminterrato = basement, Residenze = residential storeys,
  Copertura = roof), room list (`json/rooms.json`), table of spaces.
- `make_rules.py`: ILDs (residential, 1960s: heated, naturally ventilated, not cooled), InstanceBIM data, IRSs.
- `json/`: TBIM data of every step; `3d/`: BReps; `img/`: views exported from Revit.
- `Residential_1960s.rvt`: Revit 2026 model at the end of the workflow.
- `export/`: IFC4 with the TBIM property sets, InstanceBIM as topologicpy JSON, BREP, OBJ and dual graph.

Room and space names are in Italian, as in the original drawings (soggiorno = living room, letto = bedroom,
cucina = kitchen, bagno = bathroom, scala = stair, autorimessa/box = garage, sottotetto = attic).

To rebuild the inputs (Python 3.12 with the TBIM requirements):

```bat
python make_model.py
python make_rules.py
```

then open an empty Revit model, **Project > Open** this folder and run the TBIM workflow (see the
[user manual](../../docs/USER_MANUAL.md)).

## Simplifications

- The raised floor uses the typical plan, with the entrance hall in place of the east living room.
- Balconies, eaves overhang, chimneys and the cellars below the basement are not modelled.
- Windows and doors come from a stand-in of the TopologicalBIM panel (rules by room type).
- Thermal zones follow the TBIM zoning rules: one heated zone per storey (central heating), stairs,
  garages and attic apart.
