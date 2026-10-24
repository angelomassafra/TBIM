"""Activate the TBIM project linked to the opened Revit model (Project > New / Open)."""
import os

from tbim import projects, revit

doc = __eventargs__.Document  # noqa: F821
folder = revit.project_folder(doc) if doc is not None and not doc.IsFamilyDocument else None
if folder and projects.is_project(folder) and os.path.normcase(folder) != os.path.normcase(
        projects.active_project() or ""):
    projects.activate(folder)
