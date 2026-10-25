# TBIM - Topological BIM for pyRevit

**Topological BIM (TBIM)** turns a simple 3D massing model into a BIM model rich in the data needed for
building performance management: building storeys, spaces, walls, floors, roofs, windows and doors,
occupancy, internal loads, thermal zones and rule-based element types.

TBIM is built on [topologicpy](https://github.com/wassimj/topologicpy) (non-manifold topology) and runs in
Autodesk Revit as a [pyRevit](https://github.com/pyrevitlabs/pyRevit) extension. It is the open-source
implementation of:

> A. Massafra, W. Jabi, R. Gulli, *Topological BIM for building performance management*,
> Automation in Construction 166 (2024) 105628. https://doi.org/10.1016/j.autcon.2024.105628

![Six buildings building themselves with TBIM](docs/video/tbim_six_buildings.gif)

*Six example buildings going through the TBIM workflow at the same time ([MP4, 1080p](docs/video/tbim_six_buildings.mp4)).*

## Workflow

| Step | Panel | Result |
|---|---|---|
| 0 | Project | A project folder for the building, linked to the Revit model; **Run** runs the whole workflow, **Check Model** checks it |
| 1 | 3D Model | BRep massing model (one CellComplex per building block) and Project North |
| 2 | Collectors | **Informational Controllers**: storeys, walls, floors, roofs and spaces in Revit |
| 3 | Loads | **Informational Loads**: occupancy (by hand or from a table of rooms), internal loads (ILDs) and thermal zones |
| 4 | Styles | **Informational Styles**: layered Revit types with real materials, from Informational Rule Sets (IRSs) |
| 5 | TopologicalBIM | Windows and doors on the styled CellComplex by rules on the occupancy types, placed in Revit |
| 6 | InstanceBIM | Instance data (areas, finishes, U-values, ...) written back to Revit |
| - | Visualize | Topologic model, dual graph, passage graph (doors, stairs, entrances), element types and any TBIM property in 3D views |
| - | Export | IFC with the TBIM property sets; Topologic models as JSON, BREP, OBJ, dual and passage graphs |

The [**User Manual**](docs/USER_MANUAL.md) describes every command and walks through the workflow step by
step on the Demo School.

![The TBIM workflow on the Demo School](docs/video/tbim_selfbuilding.gif)

## Requirements

| | Version tested |
|---|---|
| Autodesk Revit | 2026 |
| pyRevit | 7.0 with the CPython 3.12 engine |
| topologicpy / topologic_core | 0.9.86 / 8.0.4 |

## Quick start

1. Install [pyRevit](https://github.com/pyrevitlabs/pyRevit/releases) and download this repository
   (e.g. to `C:\tbim`).
2. Install the Python packages for Python 3.12 in a local (not synced) folder:

   ```bat
   py -3.12 -m pip install -r C:\tbim\requirements.txt --target "%LOCALAPPDATA%\tbim\site-packages"
   ```

3. *pyRevit > Settings > Custom Extension Directories*: add `C:\tbim\pyRevit\pyRevit_extensions`, then
   *Reload*.
4. In Revit open the **TBIM** tab and press **Installation > Check**.
5. Follow the [tutorial](docs/USER_MANUAL.md#4-tutorial-the-demo-school-step-by-step), or open an empty model,
   **Project > Open** one of the [example projects](#example-projects) and press **Project > Run**.

## Repository

```text
pyRevit/pyRevit_extensions/TBIM.extension/   the pyRevit extension
  TBIM.tab/                                  ribbon panels and commands
  lib/tbim/                                  TBIM library (topology, loads, styles, apertures, materials, Revit I/O)
templates/json/                              default ILDs, IRSs and tables of new projects
projects/                                    example projects: inputs, data of every step, Revit, IFC, Topologic
  Demo_School/                               the tutorial project
  Residential_1960s/                         anonymized 1960s residential case study
  Office_Tower/ School/ Shopping_Centre/     invented buildings generated with tools/building_kit.py
  Fortified_Farmhouse/ Town_Hall/
examples/demo/                               inputs of the tutorial and an offline run without Revit
docs/                                        user manual, images and videos
tests/                                       pytest suite (runs the workflow offline)
tools/                                       building kit of the example projects, icons, videos
legacy/                                      material of the 2023-24 release of this repository (paper data)
```

## Example projects

Every project ships its inputs, the TBIM data of every step (`json/`), the Revit 2026 model at the end of the
workflow (`.rvt`) and its exports (`export/`): IFC4 with the TBIM property sets, and the InstanceBIM as
topologicpy JSON, BREP, OBJ, dual (adjacency) and passage graphs.

| Project | Cells | Windows / doors | |
|---|---|---|---|
| [Demo School](projects/Demo_School) | 9 | 19 | Two-block school of the tutorial, 2 storeys. |
| [Residential 1960s](projects/Residential_1960s) | 112 | 190 | Anonymized residential building of the mid 1960s, reconstructed from archive drawings: 6 storeys, hipped roof. |
| [Office Tower](projects/Office_Tower) | 181 | 480 | 20-storey office tower: concrete core, ring of offices, curtain wall. |
| [School](projects/School) | 23 | 54 | Two-storey school of the 1970s with a gym under a gable roof. |
| [Shopping Centre](projects/Shopping_Centre) | 37 | 76 | Two-level mall: glazed gallery, shops, food court, department store. |
| [Fortified Farmhouse](projects/Fortified_Farmhouse) | 17 | 48 | Fortified farmhouse (*masseria*) of southern Italy around a courtyard, with a tower. |
| [Town Hall](projects/Town_Hall) | 35 | 82 | Early-20th-century town hall: council chamber, hipped roof, clock tower. |

The last five are invented: their `make_model.py` describes the floor plans as rooms with
[`tools/building_kit.py`](tools/building_kit.py), so new test buildings take a few dozen lines.

Except for the Demo School, the walls, floors and roofs of every project are layered Revit types with real
materials, different for each building type: facing-brick cavity walls and clay-tile roofs (1960s housing), a unitised curtain wall and an
inverted flat roof (tower), facing brick, precast panels and a steel-sheet gym roof (school), a ventilated
metal and terracotta facade with a glazed skylight (mall), whitewashed tuff walls on vaulted roof terraces
(farmhouse), rusticated render, exposed brick and lead (town hall). The layers are written in the
Informational Rule Sets (`stFC_Layers`), the U-values are computed from them, and the materials (colour,
conductivity, density, specific heat) come from the material library
[`lib/tbim/materials.py`](pyRevit/pyRevit_extensions/TBIM.extension/lib/tbim/materials.py); each project
README lists its constructions.

## Development

The TBIM library runs outside Revit too: `examples/demo/run_offline.py` executes the whole workflow (the
Revit-side geometry is approximated from the cells), and the tests run it on a copy of the demo. The steps
are functions of `lib/tbim/pipeline.py`, shared by the ribbon commands and Project > Run.

```bat
py -3.12 -m pip install -r requirements.txt pytest
py -3.12 -m pytest
```

Lint with `ruff check .` (settings in `pyproject.toml`).

## Citation

If you use TBIM in your research, please cite the paper above (see also [`CITATION.cff`](CITATION.cff)).

```bibtex
@article{Massafra2024TBIM,
  title   = {Topological {BIM} for building performance management},
  author  = {Massafra, Angelo and Jabi, Wassim and Gulli, Riccardo},
  journal = {Automation in Construction},
  volume  = {166},
  pages   = {105628},
  year    = {2024},
  doi     = {10.1016/j.autcon.2024.105628}
}
```

## License

[MIT](LICENSE)
