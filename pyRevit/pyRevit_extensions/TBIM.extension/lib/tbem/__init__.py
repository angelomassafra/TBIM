"""TBEM - Topological Building Energy Model: BIM-to-BEM conversion of the TBIM projects.

Library of the TBEM tab of the TBIM pyRevit extension. The TopologicalBIM (or InstanceBIM) of the active
TBIM project becomes a Honeybee model and an EnergyPlus model in three levels of detail, one ribbon panel each,
plus a panel for the simulation:

- Spatial BEM: the thermal zones as closed volumes, with their programs (occupants, lighting, equipment,
  ventilation, set-points, schedules) and ideal loads; constructions and boundaries by Honeybee defaults;
- Topological BEM: faces typed by their place in the CellComplex, inter-zone adjacencies and boundary
  conditions (outdoors, ground, adiabatic) from the topology, windows and external doors;
- Full TBEM: layered constructions from the Informational Styles, glazing, external blinds, context shading
  and airtightness;
- Energy Simulation: weather, simulation parameters, EnergyPlus run and results.

The conversion follows the BIM-to-BEM workflow of the DIGITMAN project (Massafra et al., "Topology-Driven
BIM-to-BEM for Occupancy-Based Energy Scenario Analysis in Higher-Education Buildings", step 01 of the
digitman_bim2bem repository): TBIM cells -> thermal zones -> Honeybee rooms -> EnergyPlus.

Modules are split in:

- pure Python (``files``, ``settings``, ``programs``, ``zones``, ``results``): no topologicpy, no Revit;
- Honeybee and topologicpy based, no Revit (``schedules``, ``constructions``, ``geometry``, ``model``,
  ``simulation``): CPython only, used by the tests;
- Revit API based (``pipeline``): the steps of the ribbon commands.
"""
import tbim

tbim.add_site_packages()

__version__ = "0.1.0"
