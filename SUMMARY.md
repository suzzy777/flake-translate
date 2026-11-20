# FlakeTranslate pilots: summary of all translations

(Details of the first two Java → Python pilots: `WHAT_I_TRIED.md`, `README.md`, `nondex_pilot/README.md`.)

**Goal:** Can a coding agent move a flaky-test tool (iDFlakies = order-dependent tests, NonDex =
implementation-dependent tests) to a new ecosystem so that it still finds the right flaky tests?

**Method, same for every language:** translate the tool, build a **planted twin** (a small project in the target
ecosystem with flaky tests whose answers I know), check the tool on the twin over several seeds, then run it
on real projects.

## 1. Which tools I translated, per language

| Ecosystem | iDFlakies (OD) port | NonDex (ID) port | Twin result |
|---|---|---|---|
| Python / pytest | `pyflakies` | `pynondex` | both match the Java originals' rates; 0 false positives |
| Q# (old QDK) + C# / xUnit | `qflakies` | n/a (Q# has no unordered APIs; randomness is quantum, not ordering) | all planted OD tests + the quantum NOD test found |
| C# / .NET / xUnit | `qflakies` (same runner) | `dnnondex` | all planted OD and ID tests found, 3 seeds |
| qiskit (Python, quantum) | `pyflakies` | `qnondex`: NonDex's *idea* applied to random **seeds** (new category: "seed-dependent") | 5/6 planted found (missed one that fails 1 in 200 seeds) |
| Rust / cargo test | `rustflakies` | `rsnondex` (folder listing order only) | all planted found, 3 seeds, 0 order mismatches |
| Cucumber-JVM 7 (Java) | `cukeflakies` (built by a plain agent from a short task description) | `cukenondex` (real NonDex's JVM flags + our scenario runner) | cukenondex: planted ID found in 3/3 seeds, safe and random tests not flagged |

## 2. Results on real projects

| Ecosystem | Project | OD (iDFlakies port) | ID / NonDex port | Already known? |
|---|---|---|---|---|
| Python | mdutils (iDoFT) | **8/8 known OD + 7 polluters** | n/a | yes (iDoFT) |
| Java (originals, for reference) | marine-api, JSON-java | 12/12 OD | 6/6 ID | yes (iDoFT) |
| qiskit | qiskit-terra 0.25 | **1 OD** (`test_conditional_and_loop`, polluter changes a global controller list) | **178 seed-dependent** (separate category, not NonDex ID) | OD: no issue found; **gone in current qiskit** (pass-manager redesign removed the global controller list; tests rewritten). Seed-dependent: not checked |
| C# | Serilog | **12 OD victims**, 1 polluter (`SelfLog` never disabled), hand-confirmed | **4 ID** (reflection order) | no issue found; **all still in current Serilog** (`dev`, checked 2026-11-20): SelfLog test still never disables, ID tests still expect fixed property order |
| C# | FluentValidation | none | none | — |
| Q# | QuantumLibraries | builds and passes (283 tests); detect run not done yet | n/a | — |
| Rust | dotenvy | **7 OD victims**, 1 polluter (env vars leaked), hand-confirmed | nothing to shuffle | **yes:** issue #127 (2024), fix PR #176 (2 days old) |
| Rust | config-rs, walkdir, env_logger, tracing-subscriber | none | none / nothing to shuffle | — |
| Cucumber | generic-webhook-trigger-plugin (32 scenarios) | none | none | — |

## 3. Difficulties, and how they were fixed (often after several tries)

| Ecosystem | Problem | What I did |
|---|---|---|
| **Python** | First iDFlakies port left out two checks; a random test was reported as OD with a made-up culprit. It ran fine. | Caught only by the planted twin; added the checks. |
| | Java's flaky patterns aren't flaky in Python (`dict` and field order are guaranteed). | Mapped APIs by what the spec promises, not by class name. |
| | Python's `set` is in C and can't be swapped like Java's `HashSet`. | Rewrite project code at import time; first version missed sets in test files (0/10), fixed via pytest's assert rewriting. |
| | Python already randomizes string hashing; set order also changed with stale `.pyc` files. | Fixed `PYTHONHASHSEED`, fresh cache folder per run. |
| | Port crashed on its first real project (normal order never fully passes). | Added `--allow-failing-original`, like iDFlakies' option. |
| **Q#** | xUnit picks its own order; no way to give one. | Injected a C# file (`FtOrder.cs`) that makes xUnit run our order. |
| | Q# has no global state and a fresh simulator per test. | Planted OD tests on the C# side; expect real OD only there. |
| | Needed .NET 6 + old QDK 0.28 (repo archived). | User installed .NET 6 for their user only; checked the build first. |
| **C#** | Serilog build failed: strict nullable warnings in our injected file. | `#nullable disable` + `#pragma warning disable` in the injected file. |
| | Projects target several .NET versions; tests got counted twice ("14 duplicates" on the twin). | Pick one framework (`--framework net10.0`); stop with a clear message otherwise. |
| | xUnit cuts long test names with "···", so different cases share a name. | Merge same-name cases into one test; the worst result wins. |
| | Serilog already has its own xUnit collection settings; a second copy didn't compile. Some classes share a "collection". | Keep the project's settings; shuffle whole collections. |
| | Serilog polluter looked like "two polluters". | `[ThreadStatic]` state + async tests switching threads; confirmed by hand with 9 fixed orders. |
| | NonDex for .NET: `Dictionary`/`HashSet` can't be patched (inlined); `Assembly.GetTypes` patch fails. | Harmony patches on reflection (`GetMethods`, ...) and directory listing only. Honest limit: smaller coverage than Java NonDex. |
| | C# twin: a file-order test failed even unchanged (ext4 listing order is hash-based). | Replaced it with a stable-listing test. |
| **qiskit** | NonDex's idea doesn't fit: quantum tests are flaky through random **seeds**, not ordering. | New tool `qnondex` that changes pinned seeds; new category "seed-dependent". |
| | One qiskit test hung for 23 hours. | Per-test timeout + a file naming the running test. |
| | Bug in my run script skipped 15 test folders. | Not rerun yet. |
| **Rust** | Rust's test runner can't run tests in a given order (sorts by name). | Copied libtest's shuffle (`rsorder`) to find a shuffle seed that puts the test we want last; always check the order that really ran (0 mismatches). |
| | Each test file is its own program. | Check each test program on its own. |
| | `HashMap` is already random every run, so nothing to "NonDex". | Only shuffle folder listings, via an `LD_PRELOAD` shim over `readdir`. Honest limit: most real crates list no folders. |
| | config-rs: only 13 of its tests ran (test folder not wired up as a test program). | Reported as a weak result. |
| | tracing-subscriber: tests need optional features. | Per-project `--all-features` flag. |
| | dotenvy: test program sits in an unusual build folder. | Read the path from `cargo test --message-format=json`. |
| **Cucumber** | JUnit sees all scenarios as one test, so iDFlakies can't reorder them. | Port runs scenarios itself in one JVM in a given order (`OrderRunner`). |
| | Jenkins plugin needs Maven ≥ 3.9 ("Unknown packaging: hpi"). | Separate Maven 3.9.9 + separate library folder in `pilot/tools/`, so the computer's Maven isn't touched. |
| | First real run: 0 scenarios, reported "none" without error. Glue package guessed as `org`. | Guess glue like Cucumber does (package of the feature folder); print the runner's error when 0 scenarios run. |
| | Under Maven, the project's Cucumber suite runs 0 scenarios (project quirk), so real NonDex can't reach them. | `cukenondex`: our runner started with NonDex's own JVM flags (checked they shuffle a HashSet first). |

## 4. What this shows

1. **The algorithm carries over; the glue doesn't.** In every ecosystem, the hard part was controlling the
   order or behavior (xUnit, libtest, Cucumber, pytest), not the core logic.
2. **Some concepts don't carry over at all.** NonDex has little to shuffle in Rust and Q#, and becomes "seed
   changing" for qiskit. A translation must follow the target's rules.
3. **Broken tools look fine.** Several times a run reported "none" because it ran 0 tests, or a first
   translation ran without errors but was wrong. Planted twins and checks like "how many tests actually ran?"
   caught these.
4. **The ports find real bugs:** qiskit (1 OD), Serilog (12 OD + 4 ID), dotenvy (7 OD, matches a known
   open issue whose cause was published 2 days before).

## Limits

- All work was done in Claude Code sessions with me guiding; no automated harness, and only one plain-agent
  run (Cucumber).
- Twins are small and written by me.
- Few real projects per ecosystem.
- Seed-dependent qiskit results not checked against issues.
- Still to run: Q# detect, 15 qiskit folders.
