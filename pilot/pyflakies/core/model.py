"""Data model, translated from iDFlakies' runner.data package.

Java source: edu.illinois.cs.dt.tools.runner.data.{TestRun, DependentTest, DependentTestType}
and the Result/TestRunResult types of the testrunner library.

These are ecosystem-independent: a test is an opaque string ID, and a run is an
ordered list of IDs plus one outcome per ID. Only the integration layer knows how
an ID maps onto a JUnit method or a pytest node.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Result(str, Enum):
    PASS = "PASS"
    FAILURE = "FAILURE"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class DependentTestType(str, Enum):
    OD = "OD"
    NOD = "NOD"


@dataclass
class TestRunResult:
    """Outcome of running a list of tests in one fresh process (JVM in Java, interpreter here)."""
    id: str
    test_order: List[str]
    results: Dict[str, Result]


def before(order: List[str], test: str) -> List[str]:
    """ListUtil.before / DetectorUtil.before."""
    return list(order[: order.index(test)]) if test in order else []


@dataclass
class TestRun:
    order: List[str]
    result: Result
    test_run_id: str

    def verify(self, dt: str, runner, rounds: int = 1) -> bool:
        """TestRun.verify: rerun the prefix + dt and check the dt gets the same result."""
        for _ in range(rounds):
            order = list(self.order)
            if dt not in order:
                order.append(dt)
            new = runner.run_list(order).results.get(dt)
            print(f"Verified {dt}, status: expected {self.result.value}, got {new.value if new else None}")
            if new != self.result:
                return False
        return True


@dataclass
class DependentTest:
    name: str
    intended: TestRun
    revealed: TestRun
    type: DependentTestType = DependentTestType.OD  # "Start as OD unless proven otherwise"

    def verify(self, runner) -> bool:
        return self.intended.verify(self.name, runner) and self.revealed.verify(self.name, runner)


@dataclass
class DetectionRound:
    test_run_ids: List[str]
    unfiltered: List[DependentTest]
    filtered: List[DependentTest]
    round_time: float = 0.0
