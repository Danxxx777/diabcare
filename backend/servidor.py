#!/usr/bin/env python3
"""Launcher desde backend/ — equivalente a py -3 Principal.py"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "Principal.py"), run_name="__main__")
