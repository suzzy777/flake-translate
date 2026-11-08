from app import tags


def test_joined():
    assert tags.joined() == "alpha,gamma,beta,delta"          # PLANTED ID


def test_sorted_joined():
    assert tags.sorted_joined() == "alpha,beta,delta,gamma"   # correct


def test_local_set():
    assert ",".join({"x", "y", "z"}) == "y,z,x"                # PLANTED ID, set built in the TEST file
