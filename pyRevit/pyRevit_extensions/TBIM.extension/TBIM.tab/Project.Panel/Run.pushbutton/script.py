#! python3
"""Run the whole TBIM workflow on the active project, from the BReps to the exports."""
from tbim import pipeline, revit, ui

ctx = revit.Context(__revit__)  # noqa: F821
answer = ui.select("run_workflow", "Run the TBIM workflow",
                   ["Run every step and export (IFC and Topologic)", "Run every step, no export"])
if answer:
    try:
        done, report = pipeline.run(ctx, export_too=answer.startswith("Run every step and"))
    except pipeline.StepError as e:
        done, report = [], [str(e)]
    revit.alert("Run", "%d steps completed:\n%s" % (len(done), "\n".join(report)))
