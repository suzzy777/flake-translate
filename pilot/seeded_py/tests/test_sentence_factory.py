from app import sentence_factory as sf

class TestSentenceFactory:
    def setup_method(self):
        sf.reset()                      # every test of this class is a CLEANER

    def test_create_gga(self):
        assert isinstance(sf.create_parser("GGA"), sf.GGAParser)

    def test_unregister_vdm(self):      # POLLUTER of test_listener::test_constructor
        sf.unregister(sf.VDMParser)
        assert "VDM" not in sf._parsers
