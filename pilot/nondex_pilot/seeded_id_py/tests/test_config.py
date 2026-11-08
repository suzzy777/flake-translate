from app import config


def test_keys_csv():
    assert config.keys_csv() == "timeout,retries,port"       # Java counterpart is ID; this one is not
