#!/usr/bin/env python3
"""Arranca DiabCare desde la raíz del repo (no hace falta cd backend)."""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

if __name__ == "__main__":
    runpy.run_path(os.path.join(BACKEND, "Principal.py"), run_name="__main__")
