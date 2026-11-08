from app.cache import CACHE

def test_a_warm_cache():                # STATE-SETTER of test_b_read_cache
    CACHE["user"] = "alice"

def test_b_read_cache():                # BRITTLE: fails when run alone
    assert CACHE.get("user") == "alice"

def test_c_size():
    assert isinstance(CACHE, dict)
