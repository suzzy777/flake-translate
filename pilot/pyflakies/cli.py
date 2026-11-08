"""pyflakies: iDFlakies' random-order detector + minimizer, translated to Python/pytest.

Usage: python -m pyflakies.cli PROJECT_DIR [--rounds N] [--type random|random-class|reverse|reverse-class]
"""
from __future__ import annotations

import argparse
import json

from .core.detector import RandomDetector
from .core.minimizer import TestMinimizer
from .core.model import DependentTestType
from .integration.runner import PytestRunner, class_name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--type", default="random")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", default=None)
    ap.add_argument("--detect-only", action="store_true", help="skip the minimizer (like `mvn idflakies:detect`)")
    a = ap.parse_args(argv)

    runner = PytestRunner(a.project)
    tests = runner.list_tests()
    print(f"[INFO] {len(tests)} tests")
    det = RandomDetector(a.type, runner, a.rounds, tests, class_name, a.seed)
    dts = det.detect()
    detect_runs = runner.count

    report = []
    for dt in dts:
        entry = {"test": dt.name, "type": dt.type.value}
        if dt.type == DependentTestType.OD and not a.detect_only:
            # Minimize on the order in which the test does NOT get its isolation result:
            # failing order for a victim (-> polluter), passing order for a brittle (-> state-setter).
            iso = runner.run_list([dt.name]).results[dt.name]
            run = dt.revealed if dt.revealed.result != iso else dt.intended
            m = TestMinimizer(run.order + [dt.name], runner, dt.name).run()
            role = "polluter" if m.expected.value != "PASS" else "state-setter"
            entry.update({"isolation": iso.value, "kind": "victim" if role == "polluter" else "brittle",
                          role + "s": [p.deps for p in m.polluters]})
            entry["type"] = m.flaky_class   # minimizer verification can demote OD -> NOD (as in Java)
        report.append(entry)

    print(json.dumps(report, indent=2))
    print(f"[INFO] pytest processes: detection={detect_runs}, total={runner.count}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"report": report, "runs_detection": detect_runs, "runs_total": runner.count}, f, indent=2)


if __name__ == "__main__":
    main()
