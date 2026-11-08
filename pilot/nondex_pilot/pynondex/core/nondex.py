"""Translated from nondex-common: NonDex.java and shuffling/ControlNondeterminism.java.

This is the decision logic only: for every call of an under-determined API (an
"opportunity"), decide whether to explore a different allowed behavior and, if so,
return a random permutation. It knows nothing about which APIs exist; the ecosystem
layer (integration/shufflers.py) calls shuffle() from inside each instrumented API.
"""
from __future__ import annotations

import random
import traceback
from typing import List, Optional, Sequence

from .config import Configuration

_PKG_MARKER = "pynondex"     # Java: skip stack frames whose class starts with "edu.illinois.nondex"


class NonDex:
    def __init__(self, config: Configuration):
        self.opportunity_count = 0
        self.actual_count = 0
        self.config = config
        self.random_number = random.Random(config.seed)
        self.is_outputting = False
        self.debug_stack: Optional[List[str]] = None

    # NonDex.getRandom: FULL shares one PRNG for the whole run; ONE makes a fresh PRNG with the
    # same seed for every call, so each call of the same size gets the same permutation.
    def _get_random(self) -> random.Random:
        if self.config.mode == "FULL":
            return self.random_number
        if self.config.mode == "ONE":
            return random.Random(self.config.seed)
        raise ValueError(f"Unrecognized option for shuffle kind: {self.config.mode}")

    def get_permutation(self, original: list, element: str) -> list:
        if self._should_explore(element):
            self._get_random().shuffle(original)
        else:
            # shuffle just to advance the PRNG (Java does the same, so that whether an earlier
            # opportunity was explored does not change the permutations of later ones)
            self._get_random().shuffle(list(original))
        return original

    def get_boolean(self, element: str, identity: bool = False) -> bool:
        result = self._get_random().random() < 0.5
        return result if self._should_explore(element) else identity

    def _should_explore(self, element: str) -> bool:
        self.opportunity_count += 1
        if not self.is_outputting and self._should_explore_for_instance() and self.config.matches(element):
            self._print_stack_if_unique_debug_point()
            self.actual_count += 1
            return True
        return False

    def _should_explore_for_instance(self) -> bool:
        return self.config.start <= self.opportunity_count <= self.config.end

    def _is_debugging_unique_point(self) -> bool:
        c = self.config
        return c.start >= 0 and c.end >= 0 and c.start == c.end and self.opportunity_count == c.start

    def _print_stack_if_unique_debug_point(self) -> None:
        if self.config.print_stack and self._is_debugging_unique_point():
            self.is_outputting = True
            try:
                frames = traceback.extract_stack()
                self.debug_stack = [f"{f.filename}:{f.lineno} in {f.name}" for f in frames
                                    if _PKG_MARKER not in f.filename.replace("\\", "/").split("/")]
            finally:
                self.is_outputting = False


_instance: Optional[NonDex] = None


def init(config: Configuration) -> NonDex:
    global _instance
    _instance = NonDex(config)
    return _instance


def instance() -> Optional[NonDex]:
    return _instance


def shuffle(original: Sequence, element: str) -> list:
    """ControlNondeterminism.shuffle: lists of size < 2 are returned untouched (no opportunity)."""
    original = list(original)
    if len(original) < 2 or _instance is None:
        return original
    return _instance.get_permutation(original, element)
