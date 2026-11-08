"""Ecosystem layer, part 1: the Python APIs whose behavior pynondex explores.

NonDex instruments ~40 JDK methods whose *specification* allows several behaviors but whose
*implementation* is deterministic (e.g. HashMap iteration order). The Python counterparts
have to be chosen per API, by reading the Python spec, not by name:

  Java API (NonDex)                         Python counterpart                 Under-determined in Python?
  ----------------------------------------  ---------------------------------  ---------------------------------------
  HashSet / HashMap.keySet iteration        set, frozenset                     YES  -> NDSet / NDFrozenSet (below)
  HashMap / ConcurrentHashMap entry order   dict                               NO   (insertion order guaranteed, 3.7+)
  IdentityHashMap, WeakHashMap              dict keyed by id(), weakref dicts  NO   (built on dict)
  File.list / listFiles                     os.listdir, os.scandir, glob,      YES  -> patched below ("arbitrary order")
                                            pathlib.Path.iterdir / glob
  Class.getDeclaredFields/Methods/...       vars(cls), cls.__dict__,           NO   (definition order, PEP 520;
                                            dataclasses.fields, dir()                dir()/inspect.getmembers are sorted)
  PriorityQueue iterator / toString         heapq lists                        not instrumented in this pilot
  DateFormat.getAvailableLocales etc.       locale.locale_alias (a dict)       NO

Only calls made on behalf of the project under test are explored ("in scope"): pytest itself
calls os.scandir during collection, and shuffling the tool's own runner is not the point.
"""
from __future__ import annotations

import glob as _glob
import os
import sys

from ..core import nondex

_PROJECT = os.path.realpath(os.environ.get("NONDEX_PROJECT", os.getcwd()))
_SELF = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _is_project_file(fn: str) -> bool:
    fn = os.path.realpath(fn) if fn and not fn.startswith("<") else ""
    return fn.startswith(_PROJECT + os.sep) and not fn.startswith(_SELF + os.sep) and "site-packages" not in fn


def _invocation_element() -> tuple:
    """NonDex.getInvocationElement: the first stack frame that is not the tool itself.
    Also returns whether any frame on the stack belongs to the project (the scope check)."""
    f = sys._getframe(2)
    element, in_scope = None, False
    while f is not None:
        fn = f.f_code.co_filename
        if element is None and not os.path.realpath(fn).startswith(_SELF + os.sep):
            element = f"{fn}:{f.f_lineno} in {f.f_code.co_name}"
        if _is_project_file(fn):
            in_scope = True
            break
        f = f.f_back
    return element or "UNKNOWN", in_scope


def _explore(items: list) -> list:
    element, in_scope = _invocation_element()
    if not in_scope:
        return items
    return nondex.shuffle(items, element)


# ---------------------------------------------------------------- set / frozenset
# CPython's set is a C type: its iteration cannot be patched in place. Instead, the import hook
# (importhook.py) wraps every set display, set comprehension and set()/frozenset() call in the
# project's modules:  {a, b}  ->  _nondex_set_({a, b}).
#
# NonDex's rule is that a NON-explored call must behave exactly like the uninstrumented API.
# A rebuilt set is not guaranteed to iterate like the original one (CPython set order depends on
# insertion history and table size, and in this pilot even on how the module was compiled), so
# each wrapper keeps the ORIGINAL set object in ._orig, mirrors every mutation into it, and
# iterates ._orig when it does not explore.

def _orig(x):
    return x._orig if isinstance(x, (NDSet, NDFrozenSet)) else x


class _NDMixin:
    _base = set

    def __iter__(self):
        return iter(_explore(list(self._base.__iter__(self._orig))))

    def __repr__(self):
        if not self:
            return f"{self._base.__name__}()"
        body = "{" + ", ".join(repr(x) for x in self) + "}"
        return body if self._base is set else f"frozenset({body})"

    def __reduce__(self):
        return (self._base, (list(self._base.__iter__(self._orig)),))


def _add_wrapped_ops(cls):
    # operations that return a NEW set: compute them on the originals, wrap the result
    for name in ("__or__", "__ror__", "__and__", "__rand__", "__sub__", "__rsub__", "__xor__", "__rxor__",
                 "union", "intersection", "difference", "symmetric_difference", "copy"):
        base_m = getattr(cls._base, name, None)
        if base_m is None:
            continue

        def m(self, *a, _m=base_m, _cls=cls):
            r = _m(self._orig, *[_orig(x) for x in a])
            return _cls(r) if isinstance(r, (set, frozenset)) else r
        m.__name__ = name
        setattr(cls, name, m)
    return cls


@_add_wrapped_ops
class NDSet(_NDMixin, set):
    _base = set

    def __init__(self, orig=()):
        orig = orig if type(orig) is set else set(_orig(orig))
        set.__init__(self, orig)
        self._orig = orig

    def pop(self):                       # "remove and return an arbitrary element"
        for x in self:
            self.remove(x)
            return x
        raise KeyError("pop from an empty set")


# in-place mutations: apply to the wrapper AND to the original, so both keep the same contents
for _name in ("add", "discard", "remove", "clear", "update", "intersection_update", "difference_update",
              "symmetric_difference_update", "__ior__", "__iand__", "__isub__", "__ixor__"):
    def _mut(self, *a, _n=_name):
        getattr(set, _n)(self._orig, *[_orig(x) for x in a])
        r = getattr(set, _n)(self, *a)
        return self if _n.startswith("__i") else r
    _mut.__name__ = _name
    setattr(NDSet, _name, _mut)


@_add_wrapped_ops
class NDFrozenSet(_NDMixin, frozenset):
    _base = frozenset

    def __new__(cls, orig=()):
        orig = orig if type(orig) is frozenset else frozenset(_orig(orig))
        obj = frozenset.__new__(cls, orig)
        obj._orig = orig
        return obj


# ---------------------------------------------------------------- directory listings

class _ShuffledScandir:
    """os.scandir returns a context-manager iterator; keep that interface."""

    def __init__(self, entries):
        self._it = iter(entries)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        pass


def install_os_patches() -> None:
    orig_listdir, orig_scandir = os.listdir, os.scandir

    def listdir(path="."):
        return _explore(orig_listdir(path))

    def scandir(path="."):
        with orig_scandir(path) as it:
            entries = list(it)
        return _ShuffledScandir(_explore(entries))

    listdir.__wrapped__, scandir.__wrapped__ = orig_listdir, orig_scandir
    os.listdir, os.scandir = listdir, scandir
    # glob.glob/iglob call os.scandir at call time, so they are covered. pathlib on Python <= 3.10
    # captured os.listdir at import time (pytest imports pathlib before any plugin), so patch it too.
    try:
        import pathlib
        acc = getattr(pathlib, "_NormalAccessor", None)
        if acc is not None and hasattr(acc, "listdir"):
            acc.listdir = staticmethod(listdir)
        if acc is not None and hasattr(acc, "scandir"):
            acc.scandir = staticmethod(scandir)
    except Exception:
        pass
    _ = _glob  # imported so that glob binds the patched os module attribute lookups
