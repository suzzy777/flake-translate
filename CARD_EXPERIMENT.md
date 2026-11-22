# Card experiment: Cucumber, 0 of 32 scenarios

Task: a fresh Claude Code agent (Opus 5.5) translates iDFlakies to Cucumber. The pipeline checks the tool
on the answer-key project and on a real project (generic-webhook-trigger-plugin, 32 scenarios).
If a check fails, the agent gets the failed checks back (round 2).

## Results

| Card | Round 1 | Round 2 (agent gets the failed checks back) |
|---|---|---|
| No card (plain agent, earlier pilot) | **0 of 32** ran; tool said "no flaky tests" (silent) | not automatic: fixed by me in a guided session |
| Old card, run 1 | 6 of 32 worked; the tool **stopped with an error** instead of saying "no flaky tests" | **32 of 32**, all checks passed; agent fixed it alone |
| Old card, run 2 | same as run 1: 6 of 32, tool stopped with an error | **32 of 32**, all checks passed (*) |
| Old card, run 3 | same: 6 of 32, tool stopped with an error; also found a planted flaky test less often than the original (3 of 5 seeds vs. 85%) | **32 of 32**, all checks passed; agent fixed it alone |

(*) At first 2 checks failed ("tool ran the tests", "order really changes"). That was a bug in our check:
the tool cleans the project folder after each run, which also deleted the log file the check reads.
The log now lives outside the project; with the fixed check, run 2's tool passes everything.
| **Fixed card** | **32 of 32, all checks passed** | not needed |

"Stopped with an error" means the tool noticed that most scenarios did not run, and printed an error
("only 6 of 32 scenarios ran ... glue is probably wrong") instead of a result. The card's last section
asks for this. Without the card, the tool reported "no flaky tests", which looks like a clean project.

Why 6 of 32: the old card's rule made the agent look for the step code in each feature file's own
folder. In this project the step code is in one top folder (`bdd/`) that the project points Cucumber to:
- 6 scenarios in `bdd/` itself: right place, passed
- 7 in `bitbucket-cloud/`, `bitbucket-server/`: crashed (a "-" is not allowed in a Java package name)
- 19 in `github/`, `gitlab/`: no step code found ("undefined")

How round 2 fixed it: the feedback said "ran 0 tests, the project has 32" and gave a copy of the project.
The agent opened it, read `RunTest.java` (`@SelectClasspathResource("org/jenkinsci/plugins/gwt/bdd")`),
and changed its rule. No project-specific code was added.

Caveats: one run with the fixed card; I wrote both cards knowing the problem (best case). Agents read
some files outside their folder (Cucumber's jar, /tmp) but changed nothing outside it.

Runs: `pilot/pipeline/runs/exp_b_card`, `exp_b_card_2`, `exp_b_card_3`, `exp_c_fixed_card`.

## The one line that changed

**Old:** if nothing sets the glue, Cucumber uses the **package of the feature file's folder**
(e.g. `src/test/resources/com/acme/x/a.feature` -> glue `com.acme.x`).

**New:** if nothing sets the glue, Cucumber uses the **package of the folder the suite selects** (its
`@SelectClasspathResource` or `@SelectPackages`, e.g. `@SelectClasspathResource("com/acme/x")` -> glue
`com.acme.x`). That package includes all its subpackages, so every scenario in that folder and its
subfolders uses the same glue.

## Old card (full text)

### Ecosystem card: Cucumber-JVM 7 (JUnit Platform engine, Maven)

Short notes on how this ecosystem works. Use them; they are not a solution.

**How tests are found**
- A test is a scenario in a `.feature` file. Its ID is `file:line` of the `Scenario:` keyword.
  A Scenario Outline runs once per example row; here it counts as one test.
- Each step line is matched to a Java "step definition" method (`@Given`, `@When`, `@Then`). Cucumber
  finds these methods by searching the **glue** packages.
- Glue comes from, in this order: `cucumber.glue` in `@ConfigurationParameter` on the project's suite
  class or in `src/test/resources/junit-platform.properties`; if neither sets it, Cucumber uses the
  **package of the feature file's folder** (e.g. `src/test/resources/com/acme/x/a.feature` -> glue
  `com.acme.x`). Do not guess a broad package: a wrong glue gives "undefined steps" and the scenarios
  do not run.
- Real projects differ: feature files in any folder under `src/test/resources`, several suite classes,
  or no suite class at all.

**How tests are ordered**
- Through Maven/JUnit, all scenarios run inside one JVM, as children of the Cucumber engine. JUnit
  cannot be given a scenario order from outside, so an order tool has to start Cucumber itself (e.g.
  `io.cucumber.core.cli.Main` or the JUnit Platform launcher with one selector per scenario, in order)
  on the project's test classpath (`mvn dependency:build-classpath` plus `target/test-classes` and
  `target/classes`).
- Scenarios in one JVM can share state through static fields, files and system properties. That is
  where order dependence comes from.

**What is already random**: nothing by default; Cucumber runs feature files in path order.

**Silent failures to watch for**
- 0 scenarios ran, or scenarios "undefined"/"skipped" instead of passed: the tool must not report
  this as "no flaky tests". Compare the number of scenarios that ran with the number of `Scenario:` /
  `Scenario Outline:` lines in the project's feature files, and fail loudly if they differ a lot.


## New (fixed) card (full text)

### Ecosystem card: Cucumber-JVM 7 (JUnit Platform engine, Maven)

Short notes on how this ecosystem works. Use them; they are not a solution.

**How tests are found**
- A test is a scenario in a `.feature` file. Its ID is `file:line` of the `Scenario:` keyword.
  A Scenario Outline runs once per example row; here it counts as one test.
- Each step line is matched to a Java "step definition" method (`@Given`, `@When`, `@Then`). Cucumber
  finds these methods by searching the **glue** packages.
- Glue comes from, in this order: `cucumber.glue` in `@ConfigurationParameter` on the project's suite
  class or in `src/test/resources/junit-platform.properties`; if neither sets it, Cucumber uses the
  **package of the folder the suite selects** (its `@SelectClasspathResource` or `@SelectPackages`,
  e.g. `@SelectClasspathResource("com/acme/x")` -> glue `com.acme.x`). That package includes all its
  subpackages, so every scenario in that folder and its subfolders uses the same glue. Do not guess a broad package: a wrong glue gives "undefined steps" and the scenarios
  do not run.
- Real projects differ: feature files in any folder under `src/test/resources`, several suite classes,
  or no suite class at all.

**How tests are ordered**
- Through Maven/JUnit, all scenarios run inside one JVM, as children of the Cucumber engine. JUnit
  cannot be given a scenario order from outside, so an order tool has to start Cucumber itself (e.g.
  `io.cucumber.core.cli.Main` or the JUnit Platform launcher with one selector per scenario, in order)
  on the project's test classpath (`mvn dependency:build-classpath` plus `target/test-classes` and
  `target/classes`).
- Scenarios in one JVM can share state through static fields, files and system properties. That is
  where order dependence comes from.

**What is already random**: nothing by default; Cucumber runs feature files in path order.

**Silent failures to watch for**
- 0 scenarios ran, or scenarios "undefined"/"skipped" instead of passed: the tool must not report
  this as "no flaky tests". Compare the number of scenarios that ran with the number of `Scenario:` /
  `Scenario Outline:` lines in the project's feature files, and fail loudly if they differ a lot.

