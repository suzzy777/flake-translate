# FlakeTranslate pilot: iDFlakies (Java/Maven/JUnit) → pyflakies (Python/pytest)

This is a version run with Claude Code of the FlakeTranslate workflow on one small tool. It splits
iDFlakies into its **core logic** and its **ecosystem integration**, translates the core,
rewires the integration to pytest, and then checks the result against flaky tests that
were planted with known answers and against the original Java tool.

## 1. Decomposition of iDFlakies

| Layer | iDFlakies (Java) | pyflakies (Python) |
|---|---|---|
| **Core**: data model | `runner/data/{TestRun,DependentTest}.java` | `pyflakies/core/model.py` |
| **Core**: order generation | `detection/TestShuffler.java` | `pyflakies/core/shuffler.py` |
| **Core**: detection loop, filters, classifier | `ExecutingDetector`, `RandomDetector`, `DetectorUtil`, `ConfirmationFilter`, `UniqueFilter`, `NonorderClassifier` | `pyflakies/core/detector.py` |
| **Core**: polluter / state-setter search | `DeltaDebugger`, `TestMinimizerDeltaDebugger`, `TestMinimizer`, `MinimizeTestsResult.verify` | `pyflakies/core/minimizer.py` |
| **Integration**: run tests in a given order in a fresh process; one result per test | `testrunner` library + Maven Surefire + JUnit listener | `pyflakies/integration/runner.py` (one `python -m pytest` process per run) + `pytest_plugin.py` (reorders and deselects items; maps reports to results) |
| **Integration**: test identity | `pkg.Class.method`; class = text before the last `.` | pytest node ID; class = text before the last `::` (the module plays the class role for module-level tests) |

Size: about 1,470 lines of Java source were read. The translation is 462 lines of core, 124 lines of integration, and a 56-line CLI.
Not translated: the cleaner finder, historical/alphabetical/Tuscan orders, and the
result-file caching.

## 2. Validation with planted flaky tests

`seeded_py/` and `seeded_java/` contain the same project in each language: a polluter→victim pair
modelled on marine-api's `SentenceFactory`, which also has a cleaner `@Before`/`setup_method`; a brittle test with
its state-setter; a test that fails at random 25% of the time (NOD); and 8 non-flaky tests.
The expected answers are in `GROUND_TRUTH.md`.

**Detection only**, 10 rounds, seeds 1–20, original iDFlakies 2.0.0 vs. the translation:

| Planted test | iDFlakies 2.0.0 (Java) | pyflakies (Python) |
|---|---|---|
| victim `testConstructor` | 17 ok, 2 missed, 1 aborted* | 20 ok |
| brittle `testBReadCache` | 19 ok, 1 aborted* | 20 ok |
| NOD `testFlakyTimeout` | 16 ok, 1 missed, 2 labelled OD, 1 aborted* | 15 ok, 3 missed, 2 labelled OD |
| false positives | 0 | 0 |

\*Seed 16: the random test failed in all 3 original-order runs, so iDFlakies stopped with
`NoPassingOrderException`. That behavior is correct.

Both tools make the same kinds of mistakes at similar rates. A NOD test is labelled OD when both
confirmation reruns happen to reproduce its outcome, because there is only one verification round
(`dt.verify.rounds=1`). The miss rates come from the shuffles; the Java and Python random-number
generators give different sequences for the same seed.

**Detection + minimizer** (pyflakies only, 20 seeds): the correct polluter and state-setter were
found in **20/20** seeds for both OD tests.

## 3. What the pilot found (these are the kinds of problems FlakeTranslate has to handle)

1. **Translation bug caught by validation.** My first translation of `MinimizeTestsResult.verify`
   kept only the check "found tests + OD test reproduce the outcome". It left out two other checks:
   "the OD test alone does *not* reproduce it" and "no proper subset of the found tests does". As a
   result, a NOD test was reported as OD with a made-up state-setter. Running the planted tests across
   several seeds exposed this. Comparing against the Java source located it, and after the fix the
   result matches.
2. **The testing framework can override the order you ask for.** With JUnit 4's
   `@FixMethodOrder(NAME_ASCENDING)`, iDFlakies' requested within-class orders are not honored,
   so the original tool *cannot* reveal the brittle test; it never appeared in 10 rounds. pytest has
   no such override. A capability model therefore has to record "can the runner reorder tests within a
   class?" for each framework *and per test class*.
3. **The result categories differ.** JUnit separates FAILURE (assertion) from ERROR (exception). pytest
   reports any exception in the test body as `failed`. The adapter maps a failure during the test body
   to FAILURE and a failure during setup/teardown to ERROR. This doesn't affect detection, which only
   compares results within one ecosystem, but it would matter for tools that use the error type.
4. **"Fresh JVM" maps to "fresh interpreter."** Static fields map to module globals, and one Surefire
   fork maps to one pytest process. This held for the planted tests. It would *not* hold for state
   outside the process (files, databases), in either ecosystem.
5. **Hidden dependencies.** `MinimizeTestsResult` relies on the external `eunomia` library's
   `ListUtil.subsequences`, whose source is not in the repo. Its behavior had to be assumed (all
   order-preserving subsequences).
6. **Randomness.** `java.util.Random(42)` and Python's `random.Random(42)` produce different sequences, so
   concrete orders cannot be compared one-to-one. Equivalence has to be judged by *behavior over many
   seeds*, as in §2, not by matching outputs exactly. `ConfirmationFilter` uses an unseeded
   `new Random()`. pyflakies seeds it so that runs are reproducible.

## 4. How to run

```bash
python3 -m venv venv && venv/bin/pip install pytest
venv/bin/python -m pyflakies.cli seeded_py --rounds 10 --seed 1          # detection + minimizer
venv/bin/python -m pyflakies.cli seeded_py --rounds 10 --detect-only    # like `mvn idflakies:detect`
```

Original tool on the Java version:
```bash
cd seeded_java
mvn edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect -Ddetector.detector_type=random-class-method \
    -Ddt.randomize.rounds=10 -Ddt.seed=1 -Ddt.original.order=$PWD/original-order.txt
```

## 5. Limitations

- The original minimizer was not run. The `minimize` goal is not in the 2.0.0 release on Maven
  Central, and building iDFlakies from source was not done in this session. The minimizer is
  validated only against the planted answers, not against the original tool.
- The test projects are tiny. The next step is real Python projects with known OD tests (e.g., from the
  iPFlakies dataset), compared against iPFlakies, which is the existing hand-written Python port.
- The translation was done with Claude Code, with the steps guided manually. For the thesis, the same steps (decompose → map → translate → wire →
  validate) would be carried out by an agent and compared with a plain coding-agent baseline.
