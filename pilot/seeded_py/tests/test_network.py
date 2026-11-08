import random

def test_flaky_timeout():               # NOD: fails ~25% of runs regardless of order
    assert random.SystemRandom().random() > 0.25

def test_ok():
    assert True
