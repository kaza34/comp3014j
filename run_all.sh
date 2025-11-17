#!/bin/bash
# This script automates the simulation and analysis process.

echo "--- This script requires all .tcl files to be in the root directory ---"
echo "--- Make sure your Part B and C tcl files are properly named and placed ---"

# Note: This is a template. The user should ensure the .tcl files exist.
# For a fully automated script, it would need to handle file creation/modification.

echo "--- Running all simulations ---"
# Part A
ns partA/renoTrace.tcl
# ... add other simulation runs here ...

echo "--- Running analysis script ---"
python3 analyser3.py

echo "--- Workflow complete ---"
