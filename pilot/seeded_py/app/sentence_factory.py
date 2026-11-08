# Python analogue of marine-api's SentenceFactory singleton (Fig. 1 of the ICSME paper)
class VDMParser: pass
class GGAParser: pass
_DEFAULT = {"VDM": VDMParser, "GGA": GGAParser}
_parsers = dict(_DEFAULT)

def unregister(cls):
    for k, v in list(_parsers.items()):
        if v is cls:
            del _parsers[k]

def reset():
    global _parsers
    _parsers = dict(_DEFAULT)

def create_parser(kind):
    if kind not in _parsers:
        raise ValueError("no parser for " + kind)
    return _parsers[kind]()
