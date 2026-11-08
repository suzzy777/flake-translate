"""Polluter / state-setter search, translated from iDFlakies' minimizer.

Java sources translated:
  utility/deltadebug/DeltaDebugger.java          -> DeltaDebugger (verbatim algorithm)
  minimizer/TestMinimizerDeltaDebugger.java      -> TestMinimizerDeltaDebugger
  minimizer/TestMinimizer.java                   -> TestMinimizer (FIND_ALL loop, OD/NOD verification)

Not translated in this pilot: CleanerFinder (minimizer/cleaner/*), FileCache persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Optional

from .model import Result, before


class DeltaDebugger:
    def __init__(self):
        self.iterations = 0

    def check_valid(self, elements: List[str]) -> bool:
        raise NotImplementedError

    def delta_debug(self, elements: List[str], granularity: int) -> List[str]:
        self.iterations += 1
        if len(elements) < granularity:
            return elements
        # Java: (int) Math.round((double) size / granularity)  -- round half up, not banker's rounding
        chunk_size = int(len(elements) / granularity + 0.5)
        i = 0
        while i < len(elements):
            end = min(len(elements), i + chunk_size)
            chunk = elements[i:end]
            other = elements[:i] + elements[end:]
            if self.check_valid(other):
                return self.delta_debug(other, 2)
            if self.check_valid(chunk):
                return self.delta_debug(chunk, 2)
            i += chunk_size
        if len(elements) == granularity:
            return elements
        if len(elements) < granularity * 2:
            return self.delta_debug(elements, len(elements))
        return self.delta_debug(elements, granularity * 2)


class TestMinimizerDeltaDebugger(DeltaDebugger):
    def __init__(self, runner, dependent_test: str, expected: Result):
        super().__init__()
        self.runner, self.dt, self.expected = runner, dependent_test, expected
        self.runs = 0

    def check_valid(self, tests: List[str]) -> bool:
        order = list(tests)
        if self.dt not in order:
            order.append(self.dt)
        self.runs += 1
        return self.runner.run_list(order).results.get(self.dt, Result.SKIPPED) == self.expected


@dataclass
class PolluterData:
    index: int
    deps: List[str]


@dataclass
class MinimizeTestsResult:
    dependent_test: str
    expected: Result
    isolation: Result
    polluters: List[PolluterData]
    flaky_class: str = "OD"
    runs: int = 0


class TestMinimizer:
    def __init__(self, test_order: List[str], runner, dependent_test: str, find_all: bool = True):
        self.full = test_order
        self.order = before(test_order, dependent_test) if dependent_test in test_order else list(test_order)
        self.dt = dependent_test
        self.runner = runner
        self.find_all = find_all
        self.runs = 0
        self.expected = self._result(test_order)
        self.isolation = self._result([dependent_test])

    def _result(self, order: List[str]) -> Result:
        o = list(order)
        if self.dt not in o:
            o.append(self.dt)
        self.runs += 1
        return self.runner.run_list(o).results.get(self.dt, Result.SKIPPED)

    def run(self) -> MinimizeTestsResult:
        polluters: List[PolluterData] = []
        order = list(self.order)
        index = 0
        while order:
            if self._result(order) != self.expected:
                break
            dd = TestMinimizerDeltaDebugger(self.runner, self.dt, self.expected)
            deps = dd.delta_debug(list(order), 2)
            self.runs += dd.runs
            if not deps:
                break
            polluters.append(PolluterData(index, deps))
            if not self.find_all:
                break
            order = [t for t in order if t not in deps]
            index += 1
        res = MinimizeTestsResult(self.dt, self.expected, self.isolation, polluters)
        res.flaky_class = "OD" if self._verify(polluters) else "NOD"
        res.runs = self.runs
        return res

    def _verify(self, polluters: List[PolluterData], max_subsequences: int = 1000) -> bool:
        """MinimizeTestsResult.verify (VERIFY_REPEAT_COUNT = 1). For each found group:
        (1) group + dt gives the expected result; (2) dt alone does NOT; (3) no proper
        subsequence of the group does. Any failing group is dropped and the test becomes NOD.
        Note: the Java code gets subsequences from the external eunomia ListUtil; we assume
        it enumerates all order-preserving subsequences (sampled to at most 1000)."""
        bad = []
        for p in polluters:
            ok = self._result(p.deps) == self.expected
            if ok and p.deps:
                ok = self._result([]) != self.expected
                subs = [list(c) for k in range(1, len(p.deps)) for c in combinations(p.deps, k)]
                for s in subs[:max_subsequences]:
                    if not ok:
                        break
                    ok = self._result(s) != self.expected
            if not ok:
                bad.append(p)
        for p in bad:
            polluters.remove(p)
        return not bad
