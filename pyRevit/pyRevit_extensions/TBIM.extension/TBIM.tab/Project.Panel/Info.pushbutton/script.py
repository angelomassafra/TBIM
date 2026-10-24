"""Show the active TBIM project, its link with the Revit model and the workflow progress."""
from pyrevit import script

from tbim import paths, projects, revit

output = script.get_output()
folder = projects.active_project()
output.print_md("## TBIM project")
if folder:
    data = projects.info(folder)
    output.print_md("**%s** - %s" % (data["name"], data.get("description") or ""))
    output.print_md("Folder: `%s`" % folder)
else:
    output.print_md("No active project: the data folder `%s` is not in a project (use Project > New or Open)."
                    % paths.data_dir())

uidoc = __revit__.ActiveUIDocument  # noqa: F821
if uidoc is not None:
    linked = revit.project_folder(uidoc.Document)
    output.print_md("Revit model linked to: `%s`" % (linked or "none"))

output.print_md("### Workflow")
rows = [[step, name, "done" if exists else "-"] for step, name, exists in projects.status(folder)]
output.print_table(rows, columns=["Step", "Data file", "Status"])
output.print_md("Other projects in `%s`: %s" % (projects.projects_root(), ", ".join(
    name for name, f in projects.list_projects() if f != folder) or "none"))
