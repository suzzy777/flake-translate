# The 24 pilot mistakes: who caught them, and when

Note: the original list behind the 4/6/5/6/3 split was not saved (only the counts). This is a rebuild
from the pilot notes (`SUMMARY.md`), matched to those counts; a few rows could go in another group.
"Me" = Claude Code in the guided pilot sessions.

| # | Mistake | Who caught it | Before or after a wrong result |
|---|---|---|---|
| **Core logic (4)** | | | |
| 1 | Python iDFlakies left out 2 steps, so a random test was called OD | Answer key | **After** (wrong report on the answer key) |
| 2 | Java's flaky patterns aren't flaky in Python (dict order is promised) | Me, while translating | Before |
| 3 | qiskit: tests are flaky through seeds, not order | Me | Before |
| 4 | JS NonDex called a coin-flip test ID | Answer key | **After** (on the answer key) |
| **Test framework (6)** | | | |
| 5 | Cucumber: wrong step-code guess, so 0 of 32 ran | Me (noticed tests_run = 0) | **After**: said "no flaky tests" on a real project |
| 6 | xUnit can't be given an order | Me | Before |
| 7 | Rust can't be given an order | Me | Before |
| 8 | Jest can't be given an order | Me | Before |
| 9 | xUnit cuts long names with "···" | Me, when results didn't match | Before |
| 10 | xUnit data-row names don't match | Check: listed test had no result | Before (not fixed) |
| **Build system (5)** | | | |
| 11 | Q# needed .NET 6 and an old QDK | Build error | Before |
| 12 | Serilog: warnings in our added file | Build error | Before |
| 13 | Serilog: xUnit settings added twice | Build error | Before |
| 14 | 2 .NET versions, so tests ran twice | Answer key ("14 duplicates") | Before |
| 15 | Jenkins plugin needed Maven 3.9 | Build error | Before |
| **Runtime / OS (6)** | | | |
| 16 | Python hash randomization, old cache files | Answer key (results changed between runs) | Before |
| 17 | Python: sets in test files not shuffled (0 of 10) | Answer key | **After** (on the answer key) |
| 18 | Rust's HashMap is already random | Me | Before |
| 19 | C# Dictionary can't be patched | Me | Before |
| 20 | Node: readdir sorted, opendir not | Me | Before |
| 21 | Jest CI mode blocked snapshots | Normal run failed (jest-image-snapshot) | Before |
| **Testing its tool (3)** | | | |
| 22 | qiskit script skipped 15 folders | Me, later | **After**: results already reported, not rerun |
| 23 | config-rs: only 13 tests ran | Me (looked at the count) | **After**: "nothing found" reported, marked weak |
| 24 | C# answer-key test failed even unchanged | Me, later | **After**: the tool was blamed for it |

## Summary

- **7 of 24 were found after a wrong result** (1, 4, 5, 17, 22, 23, 24); 3 of them on real projects (5, 22, 23).
- **17 were found before any result**: mostly worked out while building, or shown by a build error.
- **Who caught them:** me 13; answer key 5; build errors 4; a failing normal run 1; a check 1. So the pilot
  mostly relied on someone noticing; the proposal makes that automatic.
- **Slide 25 fix:** "every one ran without errors" is not true (11, 12, 13, 15 and 21 failed loudly).
  Safer: "24 mistakes in the pilot; 7 gave a wrong result without any error".
