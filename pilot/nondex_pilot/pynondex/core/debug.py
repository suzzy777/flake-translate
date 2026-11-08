"""Translated from nondex-maven-plugin: DebugTask.java (and the loop in DebugMojo.java).

Given a test and the shuffled configurations in which it failed, find the single
under-determined API call ("invocation") whose exploration makes the test fail, by
binary search over the range [start, end] of explored opportunities.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

from .config import MAX_INT, MIN_INT, Configuration, SEED_FACTOR, compute_ith_seed


class DebugTask:
    def __init__(self, test: str, runner, failing_configurations: List[Configuration], class_of):
        assert failing_configurations
        self.test = test
        self.runner = runner
        self.failing_configurations = failing_configurations
        self.class_of = class_of          # ecosystem: node id -> "class" id (module or class)
        self.runs = 0

    def debug(self) -> dict:
        # Try at different levels: the test alone, its class, then the whole suite ("")
        default_test = self.test
        for test in (default_test, self.class_of(default_test), ""):
            self.test = test.split("[")[0] if "[" in test else test   # drop parametrization suffix
            result = self._try_debug_seeds()
            if result:
                return {"level": test or "<suite>", "results": result, "runs": self.runs}
        return {"level": None, "results": [], "runs": self.runs,
                "message": "cannot reproduce. may be flaky due to other causes"}

    def _try_debug_seeds(self) -> List[Configuration]:
        debugged = self._debug_with_configurations(self.failing_configurations)
        if debugged:
            return debugged
        # The seeds that failed with the full test suite no longer fail: search other seeds
        return self._debug_with_configurations(self._create_new_seeds_to_retry())

    def _create_new_seeds_to_retry(self) -> List[Configuration]:
        some = self.failing_configurations[0]
        new_seed = ((some.seed * SEED_FACTOR + 2**31) % 2**32) - 2**31   # Java int multiply wraps
        base = some.with_range(some.start, some.end, some.test_name)
        return [replace(base, seed=compute_ith_seed(i, False, new_seed)) for i in range(10)]

    def _debug_with_configurations(self, configs: List[Configuration]) -> List[Configuration]:
        out: List[Configuration] = []
        for config in configs:
            dry = self._fails_on_dry(config)
            if dry is not None:
                out += self.start_debug_binary(dry)
        return out

    def _fails_on_dry(self, config: Configuration) -> Optional[Configuration]:
        return self._fails_with_config(config, MIN_INT, MAX_INT)

    def start_debug_binary(self, config: Configuration) -> List[Configuration]:
        found: List[Configuration] = []
        pairs: List[Tuple[Tuple[int, int], Optional[Configuration]]] = [((0, config.invocations), config)]
        while pairs:
            (start, end), failing = pairs.pop(0)
            if start < end:
                ok = False
                mid = (start + end) // 2
                f = self._fails_with_config(config, start, mid)
                if f is not None:
                    pairs.append(((start, mid), f)); ok = True
                f = self._fails_with_config(config, mid + 1, end)
                if f is not None:
                    pairs.append(((mid + 1, end), f)); ok = True
                if not ok:      # neither half fails alone: the failure needs >1 exploration
                    found += self.start_debug_linear(config, start, end)
            elif failing is not None:
                found.append(self._report_debug_info(failing))
        return [f for f in found if f is not None]

    def start_debug_linear(self, config: Configuration, start: int, end: int) -> List[Configuration]:
        found: List[Configuration] = []
        pairs = [((start, end), config)]
        while pairs:
            (s, e), failing = pairs.pop(0)
            if s < e:
                f = self._fails_with_config(config, s, e - 1)
                if f is not None:
                    pairs.append(((s, e - 1), f))
                f = self._fails_with_config(config, s + 1, e)
                if f is not None:
                    pairs.append(((s + 1, e), f))
            elif failing is not None:
                found.append(self._report_debug_info(failing))
        return [f for f in found if f is not None]

    def _report_debug_info(self, failing: Configuration) -> Optional[Configuration]:
        return self._fails_with_config(failing, failing.start, failing.end, print_stack=True)

    def _fails_with_config(self, config: Configuration, start: int, end: int,
                           print_stack: bool = False) -> Optional[Configuration]:
        """Java: run surefire on self.test with [start, end]; 'fails' = the surefire execution threw,
        i.e. ANY selected test failed (not necessarily the one being debugged)."""
        self.runs += 1
        c = self.runner.run(config.with_range(start, end, self.test or None, print_stack))
        return c if c.failed_tests else None
