"""Detection loop, filters, and classifiers.

Java sources translated:
  detection/DetectorUtil.java            -> original_results, all_pass, flaky_tests
  detection/detectors/ExecutingDetector  -> ExecutingDetector (round loop, filter chain)
  detection/detectors/RandomDetector     -> RandomDetector
  detection/filters/ConfirmationFilter   -> ConfirmationFilter
  detection/filters/UniqueFilter         -> UniqueFilter
  detection/classifiers/NonorderClassifier -> NonorderClassifier

Dropped (I/O and bookkeeping, not behavior): writing DetectionRound JSON files,
loading previously detected flaky tests from disk, progress printing.
"""
from __future__ import annotations

import random
import time
from typing import Callable, Dict, List, Set

from .model import DependentTest, DependentTestType, DetectionRound, Result, TestRun, TestRunResult, before
from .shuffler import TestShuffler


class NoPassingOrderException(Exception):
    pass


def all_pass(r: TestRunResult) -> bool:
    return all(v in (Result.PASS, Result.SKIPPED) for v in r.results.values())


def original_results(order: List[str], runner, tries: int = 3, all_must_pass: bool = True) -> TestRunResult:
    res = None
    for _ in range(tries):
        res = runner.run_list(order)
        if all_pass(res):
            return res
    if all_must_pass:
        raise NoPassingOrderException(f"No passing order for tests ({tries} runs)")
    return res


def flaky_tests(intended: TestRunResult, revealed: TestRunResult, only_first_failure: bool = False) -> List[DependentTest]:
    out: List[DependentTest] = []
    for name, ir in intended.results.items():
        rr = revealed.results.get(name)
        if rr is not None and rr != ir:
            out.append(DependentTest(
                name,
                TestRun(before(intended.test_order, name), ir, intended.id),
                TestRun(before(revealed.test_order, name), rr, revealed.id)))
            if only_first_failure:
                break
    return out


class UniqueFilter:
    def __init__(self):
        self.prev: Set[str] = set()

    def keep(self, dt: DependentTest, absolute_round: int) -> bool:
        found = dt.name in self.prev
        self.prev.add(dt.name)
        return not found


class ConfirmationFilter:
    """Rerun intended and revealed orders; if either does not reproduce, the test is NOD."""
    SAMPLING = 0.2

    def __init__(self, runner, rng: random.Random):
        self.runner = runner
        self.rng = rng                       # Java uses new Random() (unseeded); seeded here for reproducibility
        self.known_flaky: Set[str] = set()
        self.known_dep: Set[str] = set()

    def keep(self, dt: DependentTest, absolute_round: int) -> bool:
        if dt.name in self.known_flaky:
            if self.rng.random() < self.SAMPLING:
                return self._confirm(True, dt)
            dt.type = DependentTestType.NOD
            return True
        if dt.name in self.known_dep:
            if self.rng.random() < self.SAMPLING:
                return self._confirm(False, dt)
            return True
        return self._confirm(False, dt)

    def _confirm(self, is_flaky: bool, dt: DependentTest) -> bool:
        confirmed = dt.verify(self.runner)
        if not is_flaky:
            if confirmed:
                self.known_dep.add(dt.name)
            else:
                self.known_flaky.add(dt.name)
                self.known_dep.discard(dt.name)
                dt.type = DependentTestType.NOD
        if is_flaky:
            dt.type = DependentTestType.NOD
            return True
        return confirmed


class ExecutingDetector:
    def __init__(self, runner, rounds: int, name: str):
        self.runner = runner
        self.rounds = rounds
        self.name = name
        self.absolute_round = 0
        self.filters: list = []
        self.count_only_first_failure = False
        self.rounds_are_total = True

    def results(self) -> DetectionRound:
        raise NotImplementedError

    def make_dts(self, intended: TestRunResult, revealed: TestRunResult, started: float) -> DetectionRound:
        unfiltered = flaky_tests(intended, revealed, self.count_only_first_failure)
        kept = list(unfiltered)
        for f in self.filters:
            kept = [t for t in kept if f.keep(t, self.absolute_round)]
        return DetectionRound([revealed.id], unfiltered, kept, time.time() - started)

    def detect(self) -> List[DependentTest]:
        found: List[DependentTest] = []
        index = 0
        while index < self.rounds:
            rnd = self.results()
            index += 1
            print(f"[INFO] Found {len(rnd.filtered)} tests in round {index} of {self.rounds}")
            found.extend(rnd.filtered)
            if rnd.filtered and not self.rounds_are_total:
                index = 0
            self.absolute_round += 1
        return found


class RandomDetector(ExecutingDetector):
    def __init__(self, type_: str, runner, rounds: int, tests: List[str],
                 class_name: Callable[[str], str], seed: int = 42):
        super().__init__(runner, rounds, type_)
        self.tests = tests
        self.shuffler = TestShuffler(type_, tests, class_name, seed)
        self.orig = original_results(tests, runner)
        self.last_result = None
        self.last_round = None
        self.filters = [ConfirmationFilter(runner, random.Random(seed)), UniqueFilter()]

    def results(self) -> DetectionRound:
        started = time.time()
        use_shuffle = (self.last_round is None or self.last_result is None
                       or len(self.last_round.filtered) != 0)
        order = self.shuffler.shuffled_order(self.absolute_round, self.last_result, use_shuffle)
        self.last_result = self.runner.run_list(order)
        self.last_round = self.make_dts(self.orig, self.last_result, started)
        return self.last_round


class NonorderClassifier:
    """A test with two different outcomes after the *same* prefix is non-order-dependent."""

    def __init__(self):
        self.flaky: Set[str] = set()
        self.known: Dict[str, Dict[str, Result]] = {}

    def update(self, r: TestRunResult) -> None:
        for name, res in r.results.items():
            if name in self.flaky:
                continue
            key = "\x00".join(before(r.test_order, name))
            prev = self.known.setdefault(name, {}).get(key)
            if prev is None:
                self.known[name][key] = res
            elif prev != res:
                self.flaky.add(name)
