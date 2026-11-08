"""Translated from nondex-maven-plugin: NonDexMojo.java (runExecutions, postProcessExecutions,
printSummary) and Utils.computeIthSeed.

`runner` is the ecosystem adapter. It must provide run(config) -> config, which runs the
selected tests in a fresh process with that configuration and fills in
config.failed_tests / config.invocations / config.opportunities.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from .config import (DEFAULT_NUM_RUNS, DEFAULT_NUM_RUNS_WITHOUT_SHUFFLING, DEFAULT_SEED,
                     Configuration, compute_ith_seed)


@dataclass
class NonDexResult:
    executions: List[Configuration]
    clean_executions: List[Configuration]
    failures_per_test: Dict[str, int] = field(default_factory=dict)   # over the shuffled executions

    @property
    def all_failures(self) -> List[str]:
        return list(self.failures_per_test)

    @property
    def failed_in_clean(self) -> List[str]:
        out: List[str] = []
        for c in self.clean_executions:
            out += [t for t in c.failed_tests if t not in out]
        return out


def nondex(runner, num_runs: int = DEFAULT_NUM_RUNS, seed: int = DEFAULT_SEED, mode: str = "FULL",
           filter: str = ".*", rerun: bool = False,
           num_runs_without_shuffling: int = DEFAULT_NUM_RUNS_WITHOUT_SHUFFLING) -> NonDexResult:
    clean = []
    for _ in range(num_runs_without_shuffling):
        clean.append(runner.run(Configuration(shuffle=False)))
    executions = []
    for i in range(num_runs):
        executions.append(runner.run(Configuration(mode=mode, seed=compute_ith_seed(i, rerun, seed),
                                                   filter=filter)))
    # postProcessExecutions: a test that fails without shuffling is not reported
    for c in clean:
        for e in executions:
            e.filter_tests(c.failed_tests)
    counts: Counter = Counter()
    for e in executions:
        counts.update(e.failed_tests)
    return NonDexResult(executions, clean, dict(counts))
