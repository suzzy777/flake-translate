"""Translated from nondex-common: Configuration.java, ConfigurationDefaults.java, Utils.computeIthSeed.

Java passes the configuration to the forked test JVM as -D system properties; here it is
passed to the fresh pytest process as environment variables (same names, NONDEX_ prefix).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from typing import List, Optional

SEED_FACTOR = 0xA1E4          # ConfigurationDefaults.SEED_FACTOR
DEFAULT_SEED = 933178         # ConfigurationDefaults.DEFAULT_SEED_STR
DEFAULT_NUM_RUNS = 3
DEFAULT_NUM_RUNS_WITHOUT_SHUFFLING = 1
DEFAULT_FILTER = ".*"
DEFAULT_START = 0
DEFAULT_END = 9223372036854775807   # Long.MAX_VALUE
MIN_LONG, MAX_INT, MIN_INT = -9223372036854775808, 2147483647, -2147483648


def compute_ith_seed(i: int, rerun: bool, seed: int) -> int:
    """Utils.computeIthSeed. Java int arithmetic wraps at 32 bits; emulate that."""
    if rerun:
        return seed
    v = (seed + i * SEED_FACTOR) & 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v


@dataclass
class Configuration:
    mode: str = "FULL"               # FULL | ONE
    seed: int = DEFAULT_SEED
    filter: str = DEFAULT_FILTER
    start: int = DEFAULT_START
    end: int = DEFAULT_END
    print_stack: bool = False
    test_name: Optional[str] = None  # pytest selection: node id, class/module id, or None = whole suite
    shuffle: bool = True             # False = CleanSurefireExecution (no instrumentation)
    # filled in after the run (the Java code reads these back from files in .nondex/<execId>/)
    failed_tests: List[str] = field(default_factory=list)
    invocations: int = 0             # "SHUFFLES:" count (Configuration.getInvocationCount)
    opportunities: int = 0           # "COUNT:"
    debug_stack: Optional[List[str]] = None

    def to_env(self) -> dict:
        return {"NONDEX_MODE": self.mode, "NONDEX_SEED": str(self.seed), "NONDEX_FILTER": self.filter,
                "NONDEX_START": str(self.start), "NONDEX_END": str(self.end),
                "NONDEX_PRINTSTACK": "true" if self.print_stack else "false",
                "NONDEX_SHUFFLE": "true" if self.shuffle else "false"}

    @staticmethod
    def from_env(env=os.environ) -> "Configuration":
        return Configuration(mode=env.get("NONDEX_MODE", "FULL"),
                             seed=int(env.get("NONDEX_SEED", DEFAULT_SEED)),
                             filter=env.get("NONDEX_FILTER", DEFAULT_FILTER),
                             start=int(env.get("NONDEX_START", DEFAULT_START)),
                             end=int(env.get("NONDEX_END", DEFAULT_END)),
                             print_stack=env.get("NONDEX_PRINTSTACK", "false") == "true",
                             shuffle=env.get("NONDEX_SHUFFLE", "true") == "true")

    def with_range(self, start: int, end: int, test: Optional[str], print_stack: bool = False) -> "Configuration":
        """The NonDexSurefireExecution(config, start, end, print, test, ...) constructor."""
        return replace(self, start=start, end=end, test_name=test, print_stack=print_stack,
                       failed_tests=[], invocations=0, opportunities=0, debug_stack=None)

    def to_argline(self) -> str:
        s = (f"--mode {self.mode} --seed {self.seed} --filter '{self.filter}' "
             f"--start {self.start} --end {self.end}")
        return s + (f" {self.test_name}" if self.test_name else "")

    def filter_tests(self, failed_in_clean) -> None:
        """Configuration.filterTests: drop tests that also fail without shuffling."""
        bad = set(failed_in_clean)
        self.failed_tests = [t for t in self.failed_tests if t not in bad]

    def matches(self, element: str) -> bool:
        return re.fullmatch(self.filter, element) is not None
