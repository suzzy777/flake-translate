"""pynondex: NonDex (Java/Maven) translated to Python/pytest.

  python -m pynondex.cli PROJECT [--runs N] [--seed S] [--mode FULL|ONE] [--debug] [--json OUT]

Like `mvn nondex:nondex` (+ `mvn nondex:debug` with --debug).
"""
from __future__ import annotations

import argparse
import json
import os
import time

from .core.config import DEFAULT_NUM_RUNS, DEFAULT_SEED
from .core.debug import DebugTask
from .core.detector import nondex
from .integration.runner import PytestRunner, class_of


def _location(stack, project):
    """Innermost project frame of the recorded stack = the line that called the explored API."""
    if not stack:
        return None
    proj = [s for s in stack if s.startswith(project + os.sep)]
    return os.path.relpath(proj[-1], project) if proj else stack[-1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--runs", type=int, default=DEFAULT_NUM_RUNS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--mode", default="FULL", choices=["FULL", "ONE"])
    ap.add_argument("--filter", default=".*")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    runner = PytestRunner(a.project)
    t0 = time.time()
    res = nondex(runner, num_runs=a.runs, seed=a.seed, mode=a.mode, filter=a.filter)
    t_detect = time.time() - t0
    print("NonDex SUMMARY:")
    for e in res.executions:
        print(f"  seed {e.seed}: {e.failed_tests or 'No Test Failed with this configuration.'}")
    print("The following tests failed in the clean run:" if res.failed_in_clean else
          "All tests pass without NonDex shuffling", res.failed_in_clean or "")
    print("Across all seeds:")
    for t, n in res.failures_per_test.items():
        print(f"  {t}  ({n}/{a.runs} seeds)")

    report = {"failures_per_test": res.failures_per_test, "failed_in_clean": res.failed_in_clean,
              "runs": a.runs, "processes_detect": runner.count, "seconds_detect": round(t_detect, 1)}
    if a.debug:
        t1 = time.time()
        report["debug"] = {}
        proj = os.path.realpath(a.project)
        for test in res.failures_per_test:
            failing = [e for e in res.executions if test in e.failed_tests]
            d = DebugTask(test, runner, failing, class_of).debug()
            locs = sorted({_location(c.debug_stack, proj) for c in d["results"]} - {None})
            report["debug"][test] = {"level": d["level"], "locations": locs,
                                     "debugged_seeds": len(d["results"]), "runs": d["runs"]}
            print(f"DEBUG {test}: {locs or d.get('message')}  (level={d['level']}, {d['runs']} runs)")
        report["seconds_debug"] = round(time.time() - t1, 1)
        report["processes_total"] = runner.count
    if a.json:
        with open(a.json, "w") as f:
            json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
