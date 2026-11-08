| Test | Category | Related test |
|---|---|---|
| tests/test_listener.py::test_constructor | OD victim | polluter: tests/test_sentence_factory.py::TestSentenceFactory::test_unregister_vdm; cleaner: any other TestSentenceFactory test run after it |
| tests/test_cache.py::test_b_read_cache | OD brittle | state-setter: tests/test_cache.py::test_a_warm_cache |
| tests/test_network.py::test_flaky_timeout | NOD (fails ~25%) | - |
| all others | not flaky | - |
