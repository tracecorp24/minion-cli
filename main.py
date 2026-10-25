#!/usr/bin/env python3
"""
MINION-FORTRESS (KOVAN-X) v3.0 Root Launcher.
"""

import sys
from pathlib import Path

# Ensure package root is in sys.path
root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from minion_fortress.main import run_app

if __name__ == "__main__":
    run_app()
