# TBIM - Topological BIM for pyRevit

**Topological BIM (TBIM)** turns a simple 3D massing model into a BIM model rich in the data needed for
building performance management: building storeys, spaces, walls, floors, roofs, windows and doors,
occupancy, internal loads, thermal zones and rule-based element types.

TBIM is built on [topologicpy](https://github.com/wassimj/topologicpy) (non-manifold topology) and runs in
Autodesk Revit as a [pyRevit](https://github.com/pyrevitlabs/pyRevit) extension. It is the open-source
implementation of:

> A. Massafra, W. Jabi, R. Gulli, *Topological BIM for building performance management*,
> Automation in Construction 166 (2024) 105628. https://doi.org/10.1016/j.autcon.2024.105628

![The TBIM workflow on the demo project](docs/video/tbim_selfbuilding.gif)

## Workflow

| Step | Panel | Result |
|---|---|---|
| 0 | Project | A project folder for the building, linked to the Revit model |
| 1 | 3D Model | BRep massing model (one CellComplex per building block) and Project North |
| 2 | Collectors | **Informational Controllers**: storeys, walls, floors, roofs and spaces in Revit |
| 3 | Loads | **Informational Loads**: occupancy, internal loads (ILDs) and thermal zones |
| 4 | Styles | **Informational Styles**: element types from Informational Rule Sets (IRSs) |
| 5 | TopologicalBIM | Windows and doors on the styled CellComplex *(panel not yet released)* |
| 6 | InstanceBIM | Instance data (areas, finishes, U-values, ...) written back to Revit |
| - | Visualize | Topologic model, dual graph, element types and any TBIM property in 3D views |

The [**User Manual**](docs/USER_MANUAL.md) describes every command and walks through the workflow step by
step on the Demo School.

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
5. Follow the [tutorial](docs/USER_MANUAL.md#4-tutorial-the-demo-school-step-by-step).

## Repository

```text
pyRevit/pyRevit_extensions/TBIM.extension/   the pyRevit extension
  TBIM.tab/                                  ribbon panels and commands
  lib/tbim/                                  TBIM library (topology, loads, styles, Revit I/O)
templates/json/                              default ILDs, IRSs and tables of new projects
projects/                                    example projects (data of every step)
  Demo_School/                               the tutorial project
  Residential_1960s/                         anonymized 1960s residential case study
examples/demo/                               inputs of the tutorial and an offline run without Revit
docs/                                        user manual, images and videos
tests/                                       pytest suite (runs the workflow offline)
tools/                                       development helpers (ribbon icons)
legacy/                                      material of the 2023-24 release of this repository (paper data)
```

## Example projects

| | |
|---|---|
| [Demo School](projects/Demo_School) | Two-block school of the tutorial: 9 cells, 2 storeys. |
| [Residential 1960s](projects/Residential_1960s) | Anonymized residential building of the mid 1960s, reconstructed from archive drawings: 112 cells, 6 storeys and attic, 1960s constructions and U-values. |

![The Residential 1960s case study](projects/Residential_1960s/video/tbim_residential_1960s.gif)

## Development

The TBIM library runs outside Revit too: `examples/demo/run_offline.py` executes the whole workflow with the
Revit interactions emulated, and the tests run it on a copy of the demo.

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
