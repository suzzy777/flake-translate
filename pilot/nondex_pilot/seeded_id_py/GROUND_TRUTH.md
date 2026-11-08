# Planted implementation-dependent (ID) tests: Python (same project as seeded_id_java)

| Test | Python API | Under-determined in Python? | Expected pynondex verdict | Debug location |
|---|---|---|---|---|
| `test_tags.py::test_joined` | `set` of `str` | yes | ID | `app/tags.py:6` |
| `test_tags.py::test_local_set` | `set` built in the test itself | yes | ID | `tests/test_tags.py:13` |
| `test_ids.py::test_ids` | `set` of `int` (`str(set)`) | yes (by spec; CPython orders small ints by value) | ID | `app/ids.py:2` |
| `test_config.py::test_keys_csv` | `dict` key order | **no**: insertion order is guaranteed | **not flaky** (Java counterpart is ID) | none |
| `test_record.py::test_header` | `dataclasses.fields` order | **no**: definition order is guaranteed | **not flaky** (Java counterpart is ID) | none |
| `test_reports.py::test_first_report` | `os.listdir` order | yes ("arbitrary order") | ID | `app/reports.py:5` |
| `test_tags.py::test_sorted_joined` | sorts first | n/a | not flaky | none |
| `test_misc.py::test_add` | none | n/a | not flaky | none |
| `test_misc.py::test_known_bug` | none (always fails) | n/a | not reported (fails in the clean run) | none |

Assertions match the order CPython 3.10.12 produces under pytest with `PYTHONHASHSEED=0` and no
stale bytecode cache (see README, finding 3).
