"""Open the folder of the active TBIM project in Windows Explorer."""
import os

from tbim import paths, projects

os.startfile(projects.active_project() or paths.data_dir())
