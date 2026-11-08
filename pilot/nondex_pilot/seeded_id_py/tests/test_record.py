from app import record


def test_header():
    assert record.header() == "name,age,email"               # Java counterpart is ID; this one is not
