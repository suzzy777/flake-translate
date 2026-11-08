# FlakeTranslate: why, what, is it worth it, related work

## 1. Why is a project needed? (Why not just ask Claude Code?)

Claude Code *can* translate a tool. In our pilots, it did. But:

- **It doesn't know when it's wrong.** Both first translations ran fine and gave wrong answers. Nothing in
  a normal agent session would catch that. Only planted flaky tests with known answers did.
- **Nobody checks the right thing today.** Translation work checks that translated functions behave like the
  originals (unit tests). For a flaky-test tool, the real question is different: *does the translated tool
  still find the flaky tests the original finds?*
- **The hard part is ecosystem-specific knowledge.** Examples: JUnit 4 ignoring the requested order, Python
  already shuffling string hashes, pytest owning test-file imports. An agent rediscovers these by trial and
  error every time, or misses them.

So the research isn't "an LLM translates code". It's **how to know a translated flaky-test tool is
correct, and how to make the agent get it right.**

## 2. What would be in the harness

The harness wraps an existing agent (Claude Code / Claude Agent SDK, or an open model with OpenHands).

1. **A fixed pipeline:** split the tool into core logic and glue code → map each capability to the target →
   translate the core → rebuild the glue for the target's build system, test framework, and instrumentation.
2. **Layer knowledge:** for each ecosystem, how to run tests in a given order, in a fresh process, how to
   instrument code, plus known pitfalls.
3. **Runner checks:** small automatic checks, e.g. "did the tests really run in the order I asked?",
   "is each run a fresh process?", "instrumentation installed but switched off = same results as a clean run".
4. **Twin projects:** the same small project in the source and target languages, with planted flaky tests
   and known answers, per flaky-test category (OD, ID, ...). They include "flaky in Java, correct in Python" cases.
5. **Differential comparison:** run the original on the source twin and the translation on the target twin
   over many seeds, compare the detection rates, and send mismatches back to the agent.

The agent can't edit parts 3–5, so it can't "fix" a failure by changing the test.

- **Input:** the tool's source code, the target ecosystem, and the flaky-test category the tool handles.
- **Output:** the translated tool plus a validation report.

## 3. Is it worth it? (my honest opinion)

**Yes, as one chapter of the thesis, if it's framed around validation. Not if it's framed as "LLMs translate tools".**

Arguments for:
- The pilots showed a real, repeatable problem: plausible-but-wrong translations that only known-answer tests catch.
- No existing translation work validates by tool effectiveness (see section 4).
- Even if agents get very good, the twin projects and checks still matter, as a benchmark for translated
  flaky-test tools. That's a fallback contribution.
- Real gaps exist: few or no flaky-test tools for Rust, Go, C++, and even for other *Java* setups
  (JUnit 5, TestNG, Gradle) that many tools don't support.

Risks a reviewer will raise:
- **"Claude Code already did it in your pilot."** Answer: only *with* the planted tests and my guidance.
  The evaluation must compare a plain agent with the full harness.
- **"How many tools are there to translate?"** It's a small set (iDFlakies, NonDex, iFixFlakies, FlakeSync, ...).
  Coverage of ecosystems matters more than the number of tools.
- **"Python already has iPFlakies."** That's useful: it's a hand-written port we can compare against.
- **Twin projects are made up.** Real projects (like the iDoFT runs) are needed too, and they already
  found a gap (mdutils).

## 4. Related work

### a) Code translation with LLMs (closest area)
- **AlphaTrans** (FSE 2025): repository-level Java → Python. Splits a project into fragments, translates
  them, and validates them with the project's own translated tests. About 25% of fragments pass validation.
  Validation = "functions behave the same", not "the tool still works".
  https://arxiv.org/abs/2410.24117
- **TransAGENT** (2024): multi-agent translation that fixes errors using runtime behavior.
  https://arxiv.org/html/2409.19894v2
- **ReCodeAgent** (2026): multi-agent, language-agnostic repository translation, validated with developer
  and agent-generated tests. https://arxiv.org/html/2604.07341
- **Repository-level benchmarks:**
  - RepoTransBench: best model about 21% success. https://arxiv.org/abs/2412.17744
  - TransRepo-bench / Skeleton-guided translation (EMNLP 2025 Findings). https://arxiv.org/html/2501.16050v1
  - RustRepoTrans. https://export.arxiv.org/pdf/2411.13990
  - ParEval-Repo: build systems are a main failure source. https://arxiv.org/pdf/2506.20938v2
  - RepoMod-Bench (2026): tests Claude Code and Codex; about 15% success on large projects.
    https://arxiv.org/pdf/2602.22518

  **Common finding:** builds, dependencies, and test infrastructure are where translation fails most.
  That's exactly the "glue" layer FlakeTranslate focuses on.

**The gap:** all of these treat the program as self-contained and validate with unit tests. None translates
a tool whose job is to *control how other programs' tests run*, and none validates by "does it still find
the bugs".

### b) Test framework migration
- **unittest → pytest with LLMs** (2026): about half of the migrated tests failed. Fixtures and setup were
  the hardest parts. https://arxiv.org/abs/2602.02964
- **JUnit 4 → 5:** done with rule-based tools (OpenRewrite, IntelliJ), not LLMs.
  https://symflower.com/en/company/blog/2024/tools-for-junit-4-to-5-migration/

These migrate *tests*, not *tools that run tests*. They do show that the framework layer is hard, even for LLMs.

### c) Getting arbitrary projects to build and run tests
- **ExecutionAgent** (ISSTA 2025): an LLM agent that builds and runs the tests of arbitrary projects in 14
  languages. Useful for running translated tools on real projects. Related to our build failures
  (openpojo, JSON-java signing). https://arxiv.org/html/2412.10133

### d) Flaky-test tools re-implemented by hand
- **OD detection:** iDFlakies (Java), iPFlakies (Python) https://cs.gmu.edu/~winglam/publications/2022/WangETAL22iPFlakies.pdf,
  JS-TOD (JavaScript). The same idea was built three times, separately.
- **FlaPy** (Python flaky tests at scale): reruns tests, OD-focused. https://ar5iv.labs.arxiv.org/html/2305.04793
- **NonDex** is Java-only. https://github.com/TestingResearchIllinois/NonDex I found no published Python
  equivalent. There's a new PyPI package, pytest-flakedoctor, that varies `PYTHONHASHSEED` to diagnose flaky
  tests (https://pypi.org/project/pytest-flakedoctor). I haven't checked it. It's worth reading, because it
  overlaps with pynondex.
- **Other languages have few tools.** For example, a 2025 study of flaky tests in Rust looks at root causes,
  but there are no Rust detection tools to speak of. https://arxiv.org/pdf/2502.02760
- **Multi-language study:** flakiness root causes across C, Go, Java, JavaScript, and Python are largely shared,
  which suggests the same techniques apply. https://neverworkintheory.org/2023/03/14/test-flakiness-across-programming-languages.html

### e) One-paragraph summary for the advisor
> Recent LLM translation work (AlphaTrans, TransAGENT, ReCodeAgent, RepoTransBench) shows that builds,
> dependencies, and test infrastructure are the main failure points, and validates translations with
> translated unit tests. Flaky-test tools are mostly that infrastructure, and what matters is whether they
> still find flaky tests. So far, researchers have re-implemented them by hand (iDFlakies → iPFlakies → JS-TOD),
> and NonDex has no Python version. FlakeTranslate fills this gap with a validation method (twin projects +
> differential comparison) and ecosystem knowledge, evaluated against a plain coding agent.

**Caveat:** I found these with a few web searches. Please double-check each paper before citing it. The newest ones
(ReCodeAgent, RepoMod-Bench, the unittest→pytest paper, pytest-flakedoctor) I only saw in search results.
