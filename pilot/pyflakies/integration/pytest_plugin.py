"""pytest plugin that plays the role of iDFlakies' custom JUnit/Surefire runner.

In iDFlakies, the `testrunner` library hooks into Maven Surefire to (1) run an exact
list of JUnit test methods in an exact order in a fresh JVM and (2) report a
PASS/FAILURE/ERROR/SKIPPED result per test. This plugin does the same for pytest:

  --pyflakies-order FILE   one pytest node ID per line; only these run, in this order
  --pyflakies-out FILE     JSON {"order": [...], "results": {nodeid: result}}
"""
from __future__ import annotations

import json

import pytest

_results = {}


def pytest_addoption(parser):
    g = parser.getgroup("pyflakies")
    g.addoption("--pyflakies-order", default=None)
    g.addoption("--pyflakies-out", default=None)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    path = config.getoption("--pyflakies-order")
    if not path:
        return
    with open(path) as f:
        wanted = [l.strip() for l in f if l.strip()]
    by_id = {it.nodeid: it for it in items}
    missing = [w for w in wanted if w not in by_id]
    if missing:
        raise pytest.UsageError(f"pyflakies: unknown test ids: {missing[:3]}")
    keep = [by_id[w] for w in wanted]
    deselected = [it for it in items if it.nodeid not in set(wanted)]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = keep


def pytest_runtest_logreport(report):
    # Map pytest's per-phase reports onto JUnit-style results:
    # failure in setup/teardown -> ERROR, failure in call -> FAILURE.
    cur = _results.get(report.nodeid)
    if report.failed:
        new = "FAILURE" if report.when == "call" else "ERROR"
        if cur not in ("FAILURE", "ERROR"):
            _results[report.nodeid] = new
    elif report.skipped:
        _results.setdefault(report.nodeid, "SKIPPED")
    elif report.when == "call" and cur is None:
        _results[report.nodeid] = "PASS"


def pytest_sessionfinish(session, exitstatus):
    out = session.config.getoption("--pyflakies-out")
    if out:
        order = [it.nodeid for it in session.items]
        with open(out, "w") as f:
            json.dump({"order": order, "results": _results}, f)
