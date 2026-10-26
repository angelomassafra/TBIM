"""Create a TBIM project folder, make it active and link it to the Revit model."""
from tbim import projects, revit, ui

name = ui.ask_text("project_name", "New project", "Project name:")
description = ui.ask_text("project_description", "New project", "Short description (optional):") if name else None
if name:
    try:
        folder = projects.create_project(name, description or "")
    except ValueError as e:
        folder = None
        revit.alert("Project", str(e))
    if folder:
        projects.activate(folder)
        if __revit__.ActiveUIDocument is not None:  # noqa: F821
            revit.link_project(revit.Context(__revit__), folder)  # noqa: F821
        revit.alert("Project", "Project '%s' created and activated:\n%s\n\nCopy the BReps of the 3D model in its '%s' "
                    "folder, then use 3D Model > Import." % (name, folder, projects.MODEL_FOLDER))
