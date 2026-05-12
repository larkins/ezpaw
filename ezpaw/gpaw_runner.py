"""Runner that executes a Python script with ezpaw GPAW wrapper in scope.

Usage: python -m ezpaw.gpaw_runner <script.py>
"""

import os
import sys
import runpy

# Ensure ezpaw is importable
EZPAW_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if EZPAW_DIR not in sys.path:
    sys.path.insert(0, EZPAW_DIR)

# Set LD_LIBRARY_PATH for GPAW libraries
local_lib = os.path.expanduser("~/.local/lib")
if "LD_LIBRARY_PATH" in os.environ:
    os.environ["LD_LIBRARY_PATH"] = local_lib + ":" + os.environ["LD_LIBRARY_PATH"]
else:
    os.environ["LD_LIBRARY_PATH"] = local_lib

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ezpaw.gpaw_runner <script.py>")
        sys.exit(1)

    script_path = sys.argv[1]
    if not os.path.isabs(script_path):
        script_path = os.path.abspath(script_path)

    # Run the script with ezpaw package available
    sys.argv = [script_path] + sys.argv[2:]
    runpy.run_path(script_path, run_name="__main__")
