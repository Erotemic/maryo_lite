#!/usr/bin/env python3
"""Run Mary-O Lite: `python main.py` from the project directory.

A local virtual environment is created only when graphical dependencies are
missing. `--help`, `--headless`, and unit tests require only Python's stdlib.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
REQUIRES = ("pygame", "PIL", "cairosvg")


def run(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not ("--headless" in argv or "--help" in argv or "-h" in argv or "--list-levels" in argv):
        # Source-only rasterization does not require the graphical runtime.
        required = ("PIL", "cairosvg") if "--build-assets" in argv else REQUIRES
        missing = [name for name in required if importlib.util.find_spec(name) is None]
        if missing:
            env = ROOT / ".venv"
            python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if not python.exists():
                print("Creating local .venv for Mary-O Lite...")
                venv.EnvBuilder(with_pip=True).create(env)
            print("Installing Pygame and SVG authoring dependencies into .venv...")
            try:
                subprocess.run([str(python), "-m", "pip", "install", "-e", str(ROOT)], check=True)
            except subprocess.CalledProcessError as exc:
                print("Dependency installation failed. Check internet access, or install "
                      "'pygame-ce Pillow CairoSVG' into an existing environment.", file=sys.stderr)
                return exc.returncode
            return subprocess.call([str(python), str(ROOT / "main.py"), *argv])
    from mary_o_lite.app import main
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(run())
