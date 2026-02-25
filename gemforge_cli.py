#!/usr/bin/env python
import sys
from pathlib import Path

# Support running `python gemforge_cli.py ...` from the repository root
# without requiring `pip install -e .` first.
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))

from gemforge.cli import main

if __name__ == "__main__":
    main()
