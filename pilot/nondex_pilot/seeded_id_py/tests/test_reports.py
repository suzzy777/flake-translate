import os
import tempfile

from app import reports


def test_first_report():
    d = tempfile.mkdtemp(prefix="reports")
    for n in ["report_a.txt", "report_b.txt", "report_c.txt"]:
        open(os.path.join(d, n), "w").close()
    assert reports.first_report(d) == "report_c.txt"           # PLANTED ID
