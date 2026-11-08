# Planted implementation-dependent (ID) tests: Java

| Test | Under-determined API | Expected NonDex verdict | Debug location |
|---|---|---|---|
| `TagsTest#testJoined` | `HashSet<String>` iteration | ID | `Tags.java:5` |
| `TagsTest#testLocalSet` | `HashSet` built in the test itself | ID | `TagsTest.java:5` |
| `IdsTest#testIds` | `HashSet<Integer>.toString` | ID | `Ids.java:4` |
| `ConfigTest#testKeysCsv` | `HashMap.keySet` order | ID | `Config.java:7` |
| `RecordTest#testHeader` | `Class.getDeclaredFields` order | ID | `Record.java:7` |
| `ReportsTest#testFirstReport` | `File.list` order | ID | `Reports.java:4` |
| `TagsTest#testSortedJoined` | sorts first | not flaky | none |
| `MiscTest#testAdd` | none | not flaky | none |
| `MiscTest#testKnownBug` | none (always fails) | not reported (fails in the clean run) | none |

Each assertion matches the order the JDK produces in a normal run, as a developer who wrote the
test against observed output would have done.
