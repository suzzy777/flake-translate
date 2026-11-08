# FlakeTranslate pilot 2: NonDex (Java/Maven) → pynondex (Python/pytest)

The second hand-run FlakeTranslate pilot. The first one (`../README.md`) ported iDFlakies, where
nearly everything carried over. NonDex was picked as the case where **the concept itself
does not carry over directly**. NonDex finds *implementation-dependent* (ID) tests: tests that
assume a deterministic behavior of an API whose specification allows several behaviors
(e.g. `HashMap` iteration order). Which APIs are under-determined is defined by each language's
specification, and Java's and Python's differ.

## 1. Decomposition

| Layer | NonDex (Java) | pynondex (Python) |
|---|---|---|
| **Core**: config, seeds | `Configuration`, `ConfigurationDefaults`, `Utils.computeIthSeed` | `pynondex/core/config.py` |
| **Core**: explore-or-not decision, permutation, FULL/ONE modes, invocation counting | `NonDex`, `ControlNondeterminism` | `pynondex/core/nondex.py` |
| **Core**: detection loop (clean runs, N seeded runs, filter clean failures) | `NonDexMojo` | `pynondex/core/detector.py` |
| **Core**: debug (binary, then linear search over the explored-invocation range; test → class → suite levels; retry other seeds) | `DebugTask`, `DebugMojo` | `pynondex/core/debug.py` |
| **Integration**: *which* APIs are under-determined | ~40 JDK methods (`nondex-core` holds patched copies of `HashMap`, `HashSet`, `Class`, `File`, …) | `set`/`frozenset` and directory listings only (`integration/shufflers.py`, with the mapping table in its docstring) |
| **Integration**: getting the instrumented APIs into the tests' process | `-Xbootclasspath/p` / `--patch-module` with rewritten JDK classes | AST rewrite at import time: own import hook for project modules, spliced into pytest's assertion rewriter for test modules (`integration/importhook.py`); monkeypatching for `os.listdir`/`os.scandir`/`pathlib` |
| **Integration**: run selection in a fresh process with config | Surefire fork with `-D` properties, `-Dtest=` | `python -m pytest` per run with env vars and a node-id selection (`integration/runner.py`, `pytest_plugin.py`) |

Size: about 1,790 lines of Java read (plugin + common; the patched JDK sources in `nondex-core`
were only surveyed). The port is **330 lines of core and 445 lines of integration**, plus a
73-line CLI. In the iDFlakies pilot the integration was a quarter of the core's size; here it is
larger than the core. The algorithm is simple. The work, and the risk, is in the ecosystem layer.

## 2. Validation with planted ID tests

`seeded_id_java/` and `seeded_id_py/` are the same small project in each language. The expected
answers are in each `GROUND_TRUTH.md`. Each assertion was written against the order that each runtime
actually produces, as a developer would write it.

**API mapping: the main translation decision** (rows are the planted tests):

| Under-determined in Java | Python counterpart | Under-determined in Python? | Planted test should be flagged in Python? |
|---|---|---|---|
| `HashSet<String>` iteration | `set` of `str` | yes | yes |
| `HashSet` built in the test | `set` built in the test | yes | yes |
| `HashSet<Integer>.toString` | `str(set of int)` | yes (by spec) | yes |
| `HashMap.keySet` order | `dict` keys | **no**, insertion order is guaranteed (3.7+) | **no** |
| `Class.getDeclaredFields` | `dataclasses.fields` / `vars(cls)` | **no**, definition order is guaranteed (PEP 520) | **no** |
| `File.list` | `os.listdir` / `scandir` / `glob` / `pathlib` | yes ("arbitrary order") | yes |

**Detection**: 5 base seeds × 10 runs = 50 shuffled runs per tool, plus one clean run per base seed:

| Planted test | NonDex 2.1.7 on Java | pynondex on Python | Expected rate if the order is fully shuffled |
|---|---|---|---|
| tags (`set` of `str`) | 50/50 | 50/50 | 23/24 ≈ 48/50 |
| set built in test | 41/50 | 39/50 | 5/6 ≈ 42/50 |
| ids (`set` of `int`) | 47/50 | 48/50 | 23/24 ≈ 48/50 |
| map key order | 43/50 | **0/50 (correct)** | n/a |
| field order | 42/50 | **0/50 (correct)** | n/a |
| directory listing (first entry) | 35/50 | 30/50 | 2/3 ≈ 33/50 |
| sorted / correct tests | 0 | 0 | 0 |
| always-failing test | filtered (fails in clean run) | filtered | n/a |

**Debug** (default seed 933178, 10 runs, then debug on every flagged test):

| Planted test | NonDex debug location | pynondex debug location |
|---|---|---|
| tags | `Tags.java:5` | `app/tags.py:6` |
| set built in test | `TagsTest.java:5` | `tests/test_tags.py:13` |
| ids | `Ids.java:4` | `app/ids.py:2` |
| map key order | `Config.java:7` | not flagged (correct) |
| field order | `Record.java:7` | not flagged (correct) |
| directory listing | `Reports.java:4` | `app/reports.py:5` |
| time for detect + debug | 6 s + 4 min 26 s (Maven, Surefire forks) | 6 s + 76 s (152 pytest processes) |

Both tools point to the exact source line of the under-determined call in every case.

**Baseline: plain pytest, 50 runs, no tool.** Python randomizes `str` hashing in every new
process, so plain pytest *already* fails the tags test (49/50) and the set-built-in-test test
(43/50). It never fails the `int` set or `os.listdir` tests (0/50). In Python, NonDex's added
value is concentrated on non-`str` sets and filesystem order, plus turning the `str`-set failures
into reproducible ones (fixed seed) with a source location.

## 3. What the pilot found

1. **The concept is redefined by the target language's spec.** Two of the six Java ID patterns
   (`HashMap` order, reflection order) are *correct* code in Python. A name-based port (`HashMap` →
   `dict`) would shuffle `dict` iteration and report false positives on valid tests. The
   translation must map *specifications*, not class names. FlakeTranslate needs a per-API "is this
   under-determined in the target spec?" step, and planted tests whose expected answer is
   **"not flaky in the target"**.
2. **Python already does a coarse NonDex.** Per-process `str` hash randomization makes `str`-set ID
   tests fail on their own. The port therefore has to *fix* `PYTHONHASHSEED` in every run (clean and
   shuffled). Otherwise the clean run is itself random, its failures are filtered out, and the ID
   tests vanish from the report.
3. **Hidden state in the Python runtime changed the "deterministic" order.** With the hash seed fixed,
   a 4-element set literal still iterated differently depending on (a) whether a stale `.pyc` from a
   run under another hash seed existed, (b) whether the module was compiled from bytes (normal import)
   or from a string, and (c) which modules had been imported before it (`importlib.metadata`, which
   pytest imports, flips it). I did not pin down the CPython internals behind (b) and (c). The port gives each run a
   fresh, empty `PYTHONPYCACHEPREFIX`, and the planted expected values were taken *under pytest*.
   Java has no equivalent. JDK `HashMap` order depends only on the keys and the insertion sequence.
4. **"Not exploring" must equal "not instrumented".** NonDex's debug search assumes an unexplored
   call behaves exactly like the uninstrumented API. Rebuilding a set to wrap it is not guaranteed
   to keep its iteration order (see 3). The wrapper therefore keeps the *original* set object, mirrors
   all mutations into it, and iterates it when not exploring. A cheap automatic check falls out of
   this. A run with instrumentation installed but zero explorations must give exactly the clean run's
   results. It does (this check is worth adding to FlakeTranslate's fixed runner checks).
5. **Built-in types can't be patched; you have to rewrite code.** Java swaps the JDK classes for
   the whole JVM. CPython's `set` is a C type, so the port rewrites set expressions in the project's
   code at import time. **A planted test exposed a gap in my first version:** it skipped test
   modules, because pytest owns their import, so a set built inside a test was never explored
   (`test_local_set`, 0/10 with the default seed). Splicing the transform into pytest's assertion rewriter fixed
   it (39/50). Sets created *inside libraries* (site-packages, the stdlib) are still not explored,
   while NonDex covers JDK-internal ones.
6. **Scope had to be added.** pytest itself calls `os.scandir` during collection. pynondex explores a
   call only when a project frame is on the stack. NonDex's default filter (`.*`) explores
   everything, including JUnit and Surefire internals.
7. **Small faithful-translation details mattered**: Java `int` overflow in seed arithmetic
   (`seed * 0xA1E4`), 1-based opportunity counting, and "advance the PRNG even when not exploring"
   (so permutations of later calls don't depend on earlier decisions).
8. **Running the original needed environment work.** On this machine a system-wide Maven
   extension silently replaces Surefire with a snapshot version that crashes. I used a private
   Maven copy without it. Also, `-Dmaven.test.failure.ignore=true` makes NonDex report **no
   failures at all**, because it parses the Surefire reports only when Surefire throws
   (`CleanSurefireExecution.run`). Both would be silent
   failures for an automated pipeline running the original as the reference.

## 4. How to run

```bash
cd nondex_pilot
python3 -m venv venv && venv/bin/pip install pytest
venv/bin/python -m pynondex.cli seeded_id_py --runs 10            # like mvn nondex:nondex
venv/bin/python -m pynondex.cli seeded_id_py --runs 10 --debug    # + mvn nondex:debug
```

Original tool on the Java version (use a Maven without the surefire-changing extension):
```bash
cd seeded_id_java
mvn edu.illinois:nondex-maven-plugin:2.1.7:nondex -DnondexRuns=10
mvn edu.illinois:nondex-maven-plugin:2.1.7:debug
```

## 5. Limitations

- Only `set`/`frozenset` and directory listings are instrumented. Other candidates, such as
  `heapq` layout, `id()`-based default hashing of objects, and `concurrent.futures.as_completed`
  (which is timing, not ID), are not.
- Sets built inside the stdlib or third-party packages are not explored. `type(s) is set` is now
  `False` for wrapped sets.
- CPython 3.10 only (`pathlib` patching differs on 3.12+).
- One tiny project with a single developer (me) choosing both the planted tests and the mapping.
  The next steps are real Python projects with known ID tests and an independent check of the API
  mapping.
- Translated by hand. For the thesis, an agent performs these steps and is compared with a plain
  coding-agent baseline.
