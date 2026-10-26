#! python3
"""Run the whole TBEM workflow on the active project: the three models and their simulations."""
from tbem import files, pipeline
from tbim import revit, ui
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
CHOICES = [("Build the three models and simulate them", files.LEVELS),
           ("Build the three models and simulate the Full TBEM", [files.FULL]),
           ("Build the three models, no simulation", [])]
answer = ui.select("tbem_run_workflow", "Run the TBEM workflow", [label for label, _ in CHOICES])
if answer:
    try:
        done, report = pipeline.run_workflow(dict(CHOICES)[answer])
    except pipeline.StepError as e:
        done, report = [], [str(e)]
    revit.alert("Run", "%d steps completed:\n%s" % (len(done), "\n".join(report)))
