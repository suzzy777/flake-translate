def tags():
    return {"beta", "alpha", "gamma", "delta"}


def joined():
    return ",".join(tags())                       # ID: set iteration order


def sorted_joined():
    return ",".join(sorted(tags()))               # correct
