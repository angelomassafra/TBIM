#! python3
"""Add the instance data of the table of spaces to the cells.

The Name of each Revit space lists the ids of the table rows it contains, separated by ';'."""
from tbim import pipeline
from tbim.revit import Context

ctx = Context(__revit__)  # noqa: F821
pipeline.command("Instance BIM", lambda: pipeline.by_table_of_spaces(ctx))
