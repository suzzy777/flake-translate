"""Ecosystem layer, part 2: getting NonDex into the code under test.

Java: NonDex rewrites the JDK classes (bytecode, at install time) and puts them in front of the
real ones with -Xbootclasspath/p (Java 8) or --patch-module (9+). Every HashSet in the JVM is
then the instrumented one.

Python: built-in types cannot be replaced. This import hook rewrites the AST of the project's
own (non-test) modules when they are imported, WRAPPING (not replacing) each set expression, so
that the original set object -- and therefore its original iteration order -- is kept:

    {a, b}            ->  _nondex_set_({a, b})
    {x for x in xs}   ->  _nondex_set_({x for x in xs})
    set(...)          ->  _nondex_set_(set(...))
    frozenset(...)    ->  _nondex_frozenset_(frozenset(...))

Membership tests against a display (`x in {1, 2}`) never iterate, so they are left alone.

Test modules are imported by pytest's own assertion-rewriting hook (a module has one loader), so
for them the same transform is spliced into pytest's rewrite_asserts() instead
(install_into_pytest_assertion_rewriting). The first version of this pilot skipped test modules,
and the planted test `test_local_set` (a set built in the test file) exposed that gap.
"""
from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import os
import sys

_NAMES = {"set": "_nondex_set_", "frozenset": "_nondex_frozenset_"}


class _SetRewriter(ast.NodeTransformer):
    def _wrap(self, node, fn="_nondex_set_"):
        return ast.copy_location(ast.Call(ast.Name(fn, ast.Load()), [node], []), node)

    def visit_Compare(self, node):
        # leave `x in {..}` / `x not in {..}` as is (CPython folds those displays to frozenset constants)
        node.left = self.visit(node.left)
        comps = []
        for op, c in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(c, ast.Set):
                self.generic_visit(c)
                comps.append(c)
            else:
                comps.append(self.visit(c))
        node.comparators = comps
        return node

    def visit_Set(self, node):
        self.generic_visit(node)
        return self._wrap(node)

    def visit_SetComp(self, node):
        self.generic_visit(node)
        return self._wrap(node)

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in _NAMES:
            return self._wrap(node, _NAMES[node.func.id])
        return node


def transform(tree: ast.Module) -> ast.Module:
    """Wrap set expressions and add the import of the wrappers (after docstring / __future__)."""
    tree = _SetRewriter().visit(tree)
    imp = ast.parse("from pynondex.integration.shufflers import "
                    "NDSet as _nondex_set_, NDFrozenSet as _nondex_frozenset_").body[0]
    body, i = tree.body, 0
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        i = 1                                                    # keep the docstring first
    while i < len(body) and isinstance(body[i], ast.ImportFrom) and body[i].module == "__future__":
        i += 1                                                   # __future__ imports must stay first
    body.insert(i, imp)
    ast.fix_missing_locations(tree)
    return tree


def rewrite(source: bytes, filename: str):
    return compile(transform(ast.parse(source, filename)), filename, "exec", dont_inherit=True)


def install_into_pytest_assertion_rewriting() -> None:
    """Test modules: pytest's AssertionRewritingHook owns their import, so run our transform on the
    module AST just before pytest rewrites its asserts (both are AST passes on the same tree)."""
    from _pytest.assertion import rewrite as pr
    orig = pr.rewrite_asserts

    def rewrite_asserts(mod, *a, **k):
        transform(mod)
        return orig(mod, *a, **k)
    pr.rewrite_asserts = rewrite_asserts


def _is_test_file(path: str) -> bool:
    b = os.path.basename(path)
    return b.startswith("test_") or b.endswith("_test.py") or b == "conftest.py"


class _Loader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        # Never read or write __pycache__: the rewritten code must not leak into normal runs.
        return rewrite(self.get_data(self.path), self.path)


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self, project: str, self_dir: str):
        self.project, self.self_dir = project, self_dir

    def find_spec(self, name, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            return None
        origin = os.path.realpath(spec.origin)
        if not origin.startswith(self.project + os.sep) or origin.startswith(self.self_dir + os.sep) \
                or "site-packages" in origin or _is_test_file(origin):
            return None
        spec.loader = _Loader(name, spec.origin)
        return spec


def install(project: str) -> None:
    self_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    sys.meta_path.insert(0, _Finder(os.path.realpath(project), self_dir))
