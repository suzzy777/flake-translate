def test_add():
    assert 2 + 2 == 4                                          # correct


def test_known_bug():
    assert 1 + 1 == 3                                          # always fails (not flaky)
