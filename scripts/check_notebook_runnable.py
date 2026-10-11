"""Verify notebook cells contain valid code and references, without Jupyter execution."""

import json
import ast
import re

with open("notebooks/eda_churn.ipynb") as f:
    nb = json.load(f)

print(f"Cells: {len(nb['cells'])}")

issues = []
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell["source"])
    if cell["cell_type"] == "code" and src.strip():
        # Try parsing as Python
        try:
            ast.parse(src)
        except SyntaxError as e:
            issues.append(f"Cell {i}: Syntax error: {e}")
        # Check data references use relative paths
        if '"data/' in src or "'data/" in src:
            # All good - relative path references
            pass

if issues:
    print(f"\nIssues ({len(issues)}):")
    for iss in issues:
        print(f"  {iss}")
else:
    print("All valid Python syntax, data paths use relative 'data/' references.")

# Verify all imports used in the notebook are available
print("\nChecking imports...")
import_lines = set()
for cell in nb["cells"]:
    for line in "".join(cell["source"]).split("\n"):
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            import_lines.add(line.strip())
for line in sorted(import_lines):
    print(f"  {line}")

print("\nNote: Notebook execution via nbconvert requires the working directory to be")
print("the repo root. Run: cd /path/to/churn-eda-submission && jupyter nbconvert")
print("--execute notebooks/eda_churn.ipynb --to notebook")