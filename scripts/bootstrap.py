"""One-command setup for SAHRA: virtual environment, install, test suite.

Stdlib only, so it can build the environment it needs. The only network it
touches is PyPI, for the project's declared dependencies and for pytest.
Importing this module does nothing: every side effect lives in main().
"""

import os
import subprocess
import sys
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
PYPROJECT = ROOT / "pyproject.toml"
TEST_RUNNER = "pytest"


def project_packages() -> list[str]:
    """The dependency list the project declares in pyproject.toml."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return list(data["project"]["dependencies"])


def venv_python(venv_dir: Path = VENV_DIR) -> Path:
    """The interpreter inside the venv, on this platform."""
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python")


def run(command: list[str]) -> tuple[int, str]:
    """Run a command from the repo root, echoing it first.

    Returns its exit code and the last non-empty line it printed.
    """
    print("$ " + " ".join(str(part) for part in command), flush=True)
    done = subprocess.run([str(part) for part in command], cwd=ROOT,
                          capture_output=True, text=True)
    output = done.stdout + done.stderr
    if output:
        print(output.rstrip("\n"), flush=True)
    lines = [line for line in output.splitlines() if line.strip()]
    return done.returncode, (lines[-1] if lines else "")


def main() -> int:
    """Create the venv if it is missing, install the project, run the tests."""
    packages = project_packages()
    print(f"SAHRA bootstrap - repo root {ROOT}")
    print(f"declared dependencies: {', '.join(packages)} (+ {TEST_RUNNER} to run the suite)")

    if VENV_DIR.exists():
        print(f"reusing the existing virtual environment {VENV_DIR}")
    else:
        print(f"creating the virtual environment {VENV_DIR}")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    python = venv_python()
    for command in ([python, "-m", "pip", "install", "-e", "."],
                    [python, "-m", "pip", "install", TEST_RUNNER]):
        code, _ = run(command)
        if code:
            print(f"command failed with exit code {code}")
            return code

    code, last = run([python, "-m", "pytest", "-q"])
    print(f"final test line: {last}")
    return code


if __name__ == "__main__":
    sys.exit(main())
