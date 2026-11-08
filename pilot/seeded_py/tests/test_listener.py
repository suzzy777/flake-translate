from app import sentence_factory as sf

def test_constructor():                 # VICTIM: needs the VDM parser
    assert isinstance(sf.create_parser("VDM"), sf.VDMParser)

def test_unrelated():
    assert 1 + 1 == 2
