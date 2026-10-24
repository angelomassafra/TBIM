import os
import sys

LIB = os.path.join(os.path.dirname(__file__), os.pardir, "pyRevit", "pyRevit_extensions", "TBIM.extension", "lib")
sys.path.insert(0, os.path.abspath(LIB))
