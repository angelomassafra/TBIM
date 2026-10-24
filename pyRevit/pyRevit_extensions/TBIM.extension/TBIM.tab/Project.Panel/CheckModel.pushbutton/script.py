#! python3
"""Check the TBIM data of the project and the Revit model: what is missing, unmatched or not styled."""
from tbim import check, revit

ctx = revit.Context(__revit__)  # noqa: F821
findings = check.project() + check.model(ctx.doc)
revit.alert("Check model", check.report(findings))
