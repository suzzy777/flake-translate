# FlakeTranslate pilots: what I tried and what went wrong

This is a plain-language log of the two FlakeTranslate pilots. The full technical write-ups are in
`README.md` (iDFlakies) and `nondex_pilot/README.md` (NonDex).

## The question

Can a coding agent (here, me, Claude) translate a flaky-test tool from Java to Python so that the
translated tool **still finds the same flaky tests**? And what goes wrong when it tries?

## What I did, step by step (same for both tools)

1. **Read the Java tool** and split it into two parts:
   - **core logic**: the idea of the tool (shuffle the test order, binary search, and so on)
   - **integration**: the glue to Maven, JUnit, and the JVM
2. **Translated the core** to Python more or less line by line.
3. **Rebuilt the integration** for pytest, because the Java glue can't be translated directly.
4. **Built "twin" test projects**: the same tiny project in Java and Python, with flaky tests
   I planted myself, so the right answers are known.
5. **Ran the original Java tool on the Java twin and my Python port on the Python twin** over many seeds,
   and compared how often each found each planted test.

I did all of this by hand, in a chat. No harness existed yet.

---

## Pilot 1: iDFlakies → pyflakies (order-dependent tests)

**What the tool does:** it runs tests in random orders. If a test passes in one order and fails in
another, that test is order-dependent (OD). It then finds which other test causes the failure.

**Size:** I read about 1,470 lines of Java. The port is 462 lines of core and 124 lines of integration.

**How I controlled the test order in pytest:** a small pytest plugin that reorders the collected tests
(`pytest_collection_modifyitems`). Each run is a fresh `python -m pytest` process, like a fresh JVM in Java.

**Results (20 seeds):**

| Planted test | Java original | Python port |
|---|---|---|
| Victim (broken by another test) | 17/20 | 20/20 |
| Brittle (needs another test to run first) | 19/20 | 20/20 |
| Random failure, correctly marked as *not* OD | 16/20 | 15/20 |
| Correct tests wrongly flagged | 0 | 0 |

The port also found the right culprit test in 20 of 20 seeds.

**Problems I ran into:**
- **My first translation was wrong and nothing looked broken.** I left out two checks in the
  final verification step, so a randomly failing test was reported as OD, with a made-up culprit.
  It ran fine. Only the planted tests caught the mistake.
- **JUnit can ignore the order you ask for.** `@FixMethodOrder` in JUnit 4 overrides the requested order,
  so when the Java test class used it, the Java tool never found the brittle test (0 of 10 rounds). pytest has no such override.
- **Different random numbers.** Java's `Random(42)` and Python's `Random(42)` produce different sequences,
  so you can't compare runs one by one. You can only compare rates over many seeds.
- **A missing dependency.** iDFlakies uses a helper from an external library whose source wasn't
  available, so I had to guess what it does.
- **Pass and fail categories differ.** JUnit separates "failure" from "error". pytest doesn't.
- **I couldn't run the original minimizer.** It isn't in the released Maven version, and building
  iDFlakies from source wasn't allowed in this session. So the culprit-finding part was checked only against
  the planted answers, not against the Java tool.

---

## Pilot 2: NonDex → pynondex (implementation-dependent tests)

**What the tool does:** some Java APIs, such as `HashSet`, have an order that the spec doesn't promise
but that happens to be fixed in practice. Tests that rely on that order are ID-flaky. NonDex
replaces those JDK classes with versions that shuffle the order, to expose these tests. It then
binary-searches for the exact line that causes the failure.

**I chose this tool because it doesn't translate cleanly.** Python's rules aren't Java's rules.

**Size:** I read about 1,790 lines of Java. The port is 330 lines of core and **445 lines of integration**.
The glue was bigger than the logic.

**Results (50 runs):**

| Planted test | Java original | Python port |
|---|---|---|
| Set order (3 tests) | 138/150 | 137/150 |
| Directory listing order | 35/50 | 30/50 |
| Map key and field order (correct code in Python) | 85/100 | 0/100, correctly |
| Correct tests wrongly flagged | 0 | 0 |

The debug step found the **same source line** as Java for every flagged test (Python: 76 s; Java: 4.5 min).

**Problems I ran into:**
- **Java's flaky patterns aren't all flaky in Python.** Python guarantees `dict` order and class field
  order. A name-based port (`HashMap` → `dict`) would flag correct tests. I had to map by
  *what the spec promises*, not by class name.
- **Python can't swap built-in classes.** Java swaps `HashSet` for the whole JVM. Python's `set` is
  written in C and can't be patched, so I rewrite the project's code when it is imported, wrapping every set.
- **My first version missed sets created inside test files** (0/10). pytest loads test files itself,
  so my import hook never saw them. A planted test caught it. I fixed it by hooking into pytest's own
  assert rewriting (now 39/50).
- **Python already shuffles some things on its own.** String hashing is random in every new process. I had to
  *fix* the hash seed (`PYTHONHASHSEED=0`). Otherwise the "clean" baseline run was random too, and the
  flaky tests got filtered out.
- **Set order changed for strange reasons.** Even with a fixed hash seed, a set's order depended on stale
  `.pyc` cache files and on which modules were imported earlier. I fixed it with a fresh cache folder per run.
  I never fully figured out why.
- **Wrapping a set must not change its order when not shuffling.** Otherwise the debug search breaks. The
  wrapper now keeps the original set and uses its order. This gave a useful automatic check:
  "instrumentation on, but no shuffling" must give exactly the clean result.
- **pytest's own code calls `os.scandir`.** I had to shuffle only calls that come from the project's code.
- **Small details mattered:** Java integer overflow in the seed arithmetic, counting calls from 1,
  and advancing the random generator even when not shuffling.
- **Running the original Java tool took environment work:**
  - A system-wide Maven extension on this machine silently forced a broken Surefire version that
    crashed. I used a private copy of Maven without it. The system wasn't changed.
  - With `-Dmaven.test.failure.ignore=true`, NonDex reports **zero failures**, silently.
  - `javac` 17 vs. `java` 8 needed `--release 8`.
  - `python -I` ignores `PYTHONHASHSEED`.

**What Python still doesn't cover:** sets created inside libraries or the standard library (NonDex does
cover JDK internals). Also, only sets and directory listings are instrumented, and only Python 3.10 was tested.

---

## What I learned (why the harness is needed)

1. **The hard part is the integration, not the algorithm.** It was a quarter of the core's size for
   iDFlakies and bigger than the core for NonDex.
2. **The first translation was wrong both times, and it looked fine.** It compiled and ran. Only
   planted tests with known answers showed the bugs. Plain "does it run?" checks wouldn't catch them.
3. **Translation has to follow the target language's rules.** Some Java flakiness isn't flakiness in Python.
   The planted projects need tests that are "flaky in Java, correct in Python".
4. **Running the original tool is itself fragile.** An automated pipeline could silently get zero results
   from the reference tool.

These four points became the harness components in the proposal: a fixed pipeline, per-ecosystem layer
knowledge, runner checks, planted twin projects, and a comparison over many seeds.

## Honest limits

- The twin projects are tiny, and I designed both the tests and the answers.
- Everything was done by hand. It isn't an automated harness yet, and there's no comparison with a plain agent yet.
- Only Java → Python, for two tools.

## Next steps

- Try real Python projects with known flaky tests (for example, the iPFlakies dataset) and compare with iPFlakies.
- Build the actual harness and compare it with a plain coding agent given the same task.
- Try more tools (iFixFlakies, my OD search, FlakeSync) and more targets (JUnit 5, TestNG, Gradle, JavaScript).
