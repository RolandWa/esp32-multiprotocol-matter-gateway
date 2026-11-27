"""pytest setup for the hardware-free tests.

Run from the repository root:   python -m pytest tests/unit -v
Only tests/unit is hardware-free - keep hardware tests elsewhere (tests/hw) so a plain
`pytest` can never touch a board by accident.
"""
import os
import sys

UNIT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(UNIT_DIR))
SCRIPTS_DIR = os.path.join(REPO, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
