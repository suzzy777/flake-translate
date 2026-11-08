"""Test-order generation, translated from iDFlakies' TestShuffler.java.

Translated: random (class + method shuffle), random-class, reverse, reverse-class,
and the "reverse the last passing order" heuristic with MD5 de-duplication.
Not translated: historical orders read from previous runs, alphabetical and Tuscan
orders (separate detectors in iDFlakies).

Deviation: java.util.Random(42) and Python's random.Random(42) produce different
sequences, so the concrete orders differ from the Java tool for the same seed.
The *distribution* of orders is the same (uniform shuffles of sorted lists).
"""
from __future__ import annotations

import hashlib
import random
from typing import Callable, Dict, List, Optional

from .model import TestRunResult


def _md5(order: List[str]) -> str:
    return hashlib.md5("".join(order).encode()).hexdigest()


class TestShuffler:
    def __init__(self, type_: str, tests: List[str], class_name: Callable[[str], str], seed: int = 42):
        self.type = type_
        self.tests = list(tests)
        self.class_name = class_name          # ecosystem-specific: injected by the integration layer
        self.random = random.Random(seed)
        self.already_seen: set = set()
        self.class_to_methods: Dict[str, List[str]] = {}
        for t in tests:
            self.class_to_methods.setdefault(class_name(t), []).append(t)

    def shuffled_order(self, index: int, last_result: Optional[TestRunResult], use_rev_passing: bool) -> List[str]:
        # NB: the Java parameter is named useRevPassing but `true` means "do NOT reverse".
        if use_rev_passing:
            return self._shuffled()
        rev = list(reversed(last_result.test_order))
        h = _md5(rev)
        if h in self.already_seen:
            return self._shuffled()
        self.already_seen.add(h)
        return rev

    def _shuffled(self) -> List[str]:
        if self.type.startswith("reverse"):
            return self._reverse_order()
        classes = sorted(self.class_to_methods)
        self.random.shuffle(classes)
        order: List[str] = []
        for c in classes:
            if self.type == "random-class":
                order.extend(self.class_to_methods[c])
            else:
                methods = sorted(self.class_to_methods[c])
                self.random.shuffle(methods)
                order.extend(methods)
        self.already_seen.add(_md5(order))
        return order

    def _reverse_order(self) -> List[str]:
        if self.type == "reverse-class":
            seen: List[str] = []
            for t in self.tests:
                c = self.class_name(t)
                if c not in seen:
                    seen.append(c)
            return [m for c in reversed(seen) for m in self.class_to_methods[c]]
        return list(reversed(self.tests))
