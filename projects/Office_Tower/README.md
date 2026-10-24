# Office Tower - TBIM example project

An invented 20-storey office tower: 30 x 30 m square plan with a central reinforced-concrete core (stairs, lifts, services) and a ring of eight office cells per storey, a double-height lobby with a cafe and shops at the ground floor and a plant room on the roof. Unitized curtain wall, post-tensioned slabs.

![The Office Tower in Revit, at the end of the TBIM workflow](img/model.png)

The building was generated and run through the complete TBIM workflow automatically: it is one of the six
buildings of the [six-building video](../../docs/video/tbim_six_buildings.mp4).

## Model

| | |
|---|---|
| Cells (rooms) | 181 |
| Building storeys | 22 |
| Revit | 484 walls, 181 floors, 9 roofs, 181 spaces, 236 windows, 244 doors |
| Thermal zones | 101 |
| Occupancy types | Office:OpenPlan, Office:Private, Office:MeetingRoom, Office:Reception, Circulation:Core, Circulation:Lobby, Food:Cafe, Retail:Shop, Technical:Plant |

## Constructions

Informational Rule Sets: each style is a layered Revit type whose materials (colour, conductivity, density, specific heat) come from the TBIM material library ([`lib/tbim/materials.py`](../../pyRevit/pyRevit_extensions/TBIM.extension/lib/tbim/materials.py)). Layers from the outside (top) to the inside (bottom), thicknesses in mm; U-values in W/(m2 K), computed from the layers (given for glazing).

| Element | Type | Layers | U |
|---|---|---|---|
| External walls | `TBIM_Unitised_Curtain_Wall_200` | Triple glazing unit 54 / Insulated spandrel panel 146 | 1.00 |
| External walls (next to: Plant) | `TBIM_Plant_Louvre_Screen_300` | Aluminium louvres 50 / Ventilated air cavity 50 / Mineral wool 100 / Precast concrete 100 | 0.32 |
| Internal walls | `TBIM_Gypsum_Stud_Partition_125` | Gypsum board 25 / Mineral wool 75 / Gypsum board 25 | 0.38 |
| Internal walls (next to: Core) | `TBIM_RC_Core_Wall_400` | Reinforced concrete 400 | 2.30 |
| Ground floor | `TBIM_Insulated_RC_Raft_620` | Natural stone tiles 20 / Cement screed 80 / XPS insulation 120 / Reinforced concrete 400 | 0.25 |
| Floors | `TBIM_PT_Slab_Raised_Floor_400` | Raised access floor panel 40 / Floor void 110 / Reinforced concrete 250 | 1.59 |
| Flat roofs | `TBIM_Inverted_Flat_Roof_590` | Gravel ballast 60 / XPS insulation 160 / Bitumen membrane 10 / Lightweight concrete screed 60 / Reinforced concrete 300 | 0.19 |

## Files

| | |
|---|---|
| `make_model.py` | Floor plans (rooms as boxes), ILDs, InstanceBIM data, IRSs, room table (`tbim_Rooms.json`) and window/door rules (`tbim_TopologicalBIM_Rules.json`): writes `3d/` and `json/` |
| `3d/*.brep` | Massing model, one CellComplex per building block (centimetres) |
| `json/` | TBIM data of every step of the workflow |
| `Office_Tower.rvt` | Revit 2026 model at the end of the workflow, with the TBIM views and legends |
| `export/Office_Tower.ifc` | IFC4 Reference View with the TBIM property sets (Export > IFC) |
| `export/tbim_InstanceBIM.*` | InstanceBIM as topologicpy JSON, BREP, OBJ, dual (adjacency) and passage graphs JSON (Export > Topologic) |

## Rebuild

```bat
python make_model.py
```

then open an empty Revit model, **Project > Open** this folder and press **Project > Run**: it runs every
step of the workflow, from Collectors to the exports (occupancy types from Loads > Assignment > From Table,
windows and doors from TopologicalBIM > By Rules). **Project > Check Model** checks the result.
