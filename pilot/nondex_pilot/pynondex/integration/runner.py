"""Ecosystem adapter: run (a selection of) the pytest suite in a fresh interpreter under a
Configuration. Counterpart of CleanSurefireExecution / NonDexSurefireExecution.

  Java/Maven                                   Python/pytest (this file)
  -------------------------------------------  ------------------------------------------------
  one surefire fork = one JVM                  one `python -m pytest` process
  -D system properties carry the config        environment variables carry the config
  -Dtest=Class#method / Class / (none)         node id / module-or-class id / (none)
  JVM's String.hashCode is fixed               PYTHONHASHSEED=0 in EVERY run (see README: Python
                                               already randomizes str hashing per process)
  (no equivalent)                              fresh PYTHONPYCACHEPREFIX per run: a stale .pyc can
                                               change set-literal iteration order
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from ..core.config import Configuration

PILOT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def class_of(node_id: str) -> str:
    return node_id.rsplit("::", 1)[0]


class PytestRunner:
    def __init__(self, project: str, python: str = sys.executable, hash_seed: str = "0"):
        self.project = os.path.abspath(project)
        self.python = python
        self.hash_seed = hash_seed
        self.count = 0

    def run(self, config: Configuration) -> Configuration:
        self.count += 1
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.json")
            env = dict(os.environ)
            env.update(config.to_env())
            env.update({"PYTHONPATH": PILOT_ROOT + os.pathsep + env.get("PYTHONPATH", ""),
                        "PYTHONDONTWRITEBYTECODE": "1", "NONDEX_PROJECT": self.project, "NONDEX_OUT": out,
                        # A stale .pyc stores set literals as frozenset constants in the order of the hash
                        # seed it was COMPILED under; loaded under another seed, the set iterates in a
                        # different order. A fresh, empty cache dir per run removes that hidden state.
                        "PYTHONPYCACHEPREFIX": os.path.join(d, "pycache")})
            if self.hash_seed is not None:
                env["PYTHONHASHSEED"] = self.hash_seed
            cmd = [self.python, "-m", "pytest", "-p", "pynondex.integration.pytest_plugin",
                   "-p", "no:cacheprovider", "-p", "no:randomly", "-q", "--no-header"]
            if config.test_name:
                cmd.append(config.test_name)
            p = subprocess.run(cmd, cwd=self.project, env=env, capture_output=True, text=True)
            if not os.path.exists(out):
                raise RuntimeError(f"pytest did not run:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
            with open(out) as f:
                data = json.load(f)
        config.failed_tests = data["failed"]
        config.invocations = data["invocations"]
        config.opportunities = data["opportunities"]
        config.debug_stack = data["debug_stack"]
        return config
