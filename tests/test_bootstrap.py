# tests/test_bootstrap.py
"""The bootstrap script is part of the repo, so it is tested like the rest.

It is loaded by path: `scripts/` is not a package and must stay importable
without touching the network or the virtual environment.
"""
import importlib.util
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap.py"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("sahra_bootstrap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_exposes_main_without_running_anything(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("importing the bootstrap script must not run anything")

    monkeypatch.setattr(subprocess, "run", boom)
    module = load_bootstrap()
    assert callable(module.main)
    assert module.ROOT == ROOT


def test_the_repo_package_list_is_discoverable():
    module = load_bootstrap()
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    packages = module.project_packages()
    assert packages == declared["project"]["dependencies"]
    assert any(p.startswith("pydantic") for p in packages)


def test_help_exits_zero_without_installing_anything(monkeypatch):
    module = load_bootstrap()
    calls = []

    def record(*args, **kwargs):
        calls.append(args)
        raise AssertionError("--help must not run an install")

    monkeypatch.setattr(module, "run", record)
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--help"])
    assert exit_info.value.code == 0
    assert calls == []
