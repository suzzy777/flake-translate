# FlakeTranslate pilots: short summary

(Longer version: `WHAT_I_TRIED.md`.)

**Goal:** Can an AI agent translate a Java flaky-test tool to Python so that it still finds the same flaky tests?

**What I did:** I used Claude Code to translate two tools to Python. I built a tiny Java project and a matching Python project
with planted flaky tests, then compared the original tool with the translated one.

## Results

| Tool | What it finds | Original (Java) vs. translation (Python) |
|---|---|---|
| iDFlakies | order-dependent tests | similar detection rates (e.g., 17/20 vs. 20/20); same culprit found |
| NonDex | implementation-dependent tests | similar rates (e.g., 138/150 vs. 137/150); same buggy line found |

Neither tool flagged any correct test (0 false positives).

## Main problems

- **My first translation was wrong both times, and it still ran fine.** Only the planted tests caught the bugs.
- **The glue code was the hard part**, not the algorithm. For NonDex, the glue was bigger than the logic.
- **Java's rules aren't Python's.** Some Java flaky patterns are correct code in Python, so a word-for-word port would flag correct tests.
- **Python can't swap built-in classes the way Java does**, so I had to rewrite code as it loads.
- **Running the original Java tool was fragile.** One setting made NonDex silently report zero failures.

## Takeaway

A plain agent can produce a port that looks right but isn't. Translations need checking against flaky tests
with known answers. That's what the FlakeTranslate harness will do.

## Limits

The projects are tiny, the translations were done in a Claude Code session (not an automated harness), and only Java → Python was tried.
