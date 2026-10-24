"""Activate an existing TBIM project and link it to the Revit model."""
from tbim import projects, revit, ui

BROWSE = "Browse for a project folder..."


def browse():
    from pyrevit import forms
    folder = forms.pick_folder(title="TBIM project folder")
    question = "%s is not a TBIM project yet. Make it a project?" % folder
    if folder and (projects.is_project(folder) or forms.alert(question, title="TBIM - Open", yes=True, no=True)):
        return folder
    return None


available = projects.list_projects()
labels = ["%s  (%s)" % (name, folder) for name, folder in available] + [BROWSE]
choice = ui.select("project_open", "Open project", labels)
folder = browse() if choice == BROWSE else (available[labels.index(choice)][1] if choice else None)
if folder:
    projects.activate(folder)
    if __revit__.ActiveUIDocument is not None:  # noqa: F821
        revit.link_project(revit.Context(__revit__), folder)  # noqa: F821
    revit.alert("Project", "Active project: %s\n%s" % (projects.info(folder)["name"], folder))
