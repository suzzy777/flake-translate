"""pytest plugin loaded with -p in every run (the counterpart of NonDex's argLine for the forked JVM).

At load time (before test modules and the project are imported) it reads the configuration
from the environment and, for a shuffled run, installs the instrumentation. At the end it writes
what the Java side reads back from .nondex/<execId>/{failures,invocations,debug}.
"""
from __future__ import annotations

import json
import os

import pytest

from ..core import nondex
from ..core.config import Configuration

_config = Configuration.from_env()
_failed: list = []

if _config.shuffle:
    nondex.init(_config)
    from . import importhook, shufflers
    shufflers.install_os_patches()
    importhook.install(os.environ.get("NONDEX_PROJECT", os.getcwd()))
    importhook.install_into_pytest_assertion_rewriting()


def pytest_configure(config):
    config.addinivalue_line("markers", "nondex_ignore: do not run this test under NonDex (@NonDexIgnore)")


def pytest_collection_modifyitems(session, config, items):
    # NonDexSurefireExecution adds excludedGroups=edu.illinois.NonDexIgnore to shuffled runs only
    if not _config.shuffle:
        return
    keep = [it for it in items if it.get_closest_marker("nondex_ignore") is None]
    if len(keep) != len(items):
        config.hook.pytest_deselected(items=[it for it in items if it not in keep])
        items[:] = keep


def pytest_runtest_logreport(report):
    # surefire reports a test as failed for a failure or error in any phase
    if report.failed and report.nodeid not in _failed:
        _failed.append(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("NONDEX_OUT")
    if not out:
        return
    nd = nondex.instance()
    with open(out, "w") as f:
        json.dump({"failed": _failed,
                   "invocations": nd.actual_count if nd else 0,
                   "opportunities": nd.opportunity_count if nd else 0,
                   "debug_stack": nd.debug_stack if nd else None,
                   "collected": session.testscollected, "exitstatus": int(exitstatus)}, f)
