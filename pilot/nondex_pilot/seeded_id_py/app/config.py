def keys_csv():
    m = {}
    m["timeout"] = 30
    m["retries"] = 3
    m["port"] = 8080
    return ",".join(m.keys())                     # NOT ID in Python: dict keeps insertion order
