from dataclasses import dataclass, fields


@dataclass
class Record:
    name: str = ""
    age: int = 0
    email: str = ""


def header():
    return ",".join(f.name for f in fields(Record))   # NOT ID in Python: field definition order
