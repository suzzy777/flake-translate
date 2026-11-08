"""Ecosystem adapter: everything pytest-specific that the translated core needs.

iDFlakies concept            Java/Maven/JUnit                         Python/pytest (this file)
---------------------------  ---------------------------------------  -----------------------------------------
test ID                      fully.qualified.Class.method             pytest node ID  path.py::Class::test
"class" of a test            name up to the last '.'                  node ID up to the last '::' (module if no class)
list the test suite          Surefire scan / testrunner               pytest --collect-only -q
run list in order, fresh     testrunner + Surefire, one JVM per run   one `python -m pytest` process per run
  process                                                             + pytest_plugin reorders/deselects items
per-test result              JUnit listener                           pytest_runtest_logreport hook
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import List

from ..core.model import Result, TestRunResult

PILOT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def class_name(test_id: str) -> str:
    return test_id.rsplit("::", 1)[0]


class PytestRunner:
    def __init__(self, project_dir: str, python: str = sys.executable):
        self.project_dir = os.path.abspath(project_dir)
        self.python = python
        self.count = 0

    def _base_cmd(self) -> List[str]:
        return [self.python, "-m", "pytest", "-p", "pyflakies.integration.pytest_plugin",
                "-p", "no:cacheprovider", "-q", "--no-header", "-rN"]

    def _env(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = PILOT_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def list_tests(self) -> List[str]:
        out = subprocess.run(self._base_cmd() + ["--collect-only"], cwd=self.project_dir,
                             env=self._env(), capture_output=True, text=True)
        return [l.strip() for l in out.stdout.splitlines() if "::" in l and not l.startswith(" ")]

    def run_list(self, tests: List[str]) -> TestRunResult:
        self.count += 1
        with tempfile.TemporaryDirectory() as d:
            order_f, out_f = os.path.join(d, "order.txt"), os.path.join(d, "out.json")
            with open(order_f, "w") as f:
                f.write("\n".join(tests))
            subprocess.run(self._base_cmd() + ["--pyflakies-order", order_f, "--pyflakies-out", out_f],
                           cwd=self.project_dir, env=self._env(), capture_output=True, text=True)
            with open(out_f) as f:
                data = json.load(f)
        return TestRunResult(id=f"run-{self.count}", test_order=data["order"],
                             results={k: Result(v) for k, v in data["results"].items()})
