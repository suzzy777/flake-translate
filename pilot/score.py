"""Score pyflakies/iDFlakies reports against seeded_py/GROUND_TRUTH.md."""
import json, sys
TRUTH = {
  "test_constructor": ("OD", "test_unregister_vdm"),
  "test_b_read_cache": ("OD", "test_a_warm_cache"),
  "test_flaky_timeout": ("NOD", None),
}
def short(t): return t.replace("::", ".").split(".")[-1]
def score(report):
    got = {short(r["test"]): r for r in report}
    row = {}
    for t, (ty, rel) in TRUTH.items():
        r = got.get(t)
        if r is None: row[t] = "missed"; continue
        rels = r.get("polluters") or r.get("state-setters") or [[]]
        ok = r["type"] == ty and (rel is None or [short(x) for x in rels[0]] == [rel])
        row[t] = "ok" if ok else f"wrong({r['type']},{[short(x) for g in rels for x in g]})"
    fp = [t for t in got if t not in TRUTH]
    return row, fp
if __name__ == "__main__":
    for f in sys.argv[1:]:
        d = json.load(open(f)); row, fp = score(d["report"])
        print(f.split("/")[-1], row, "FP:", fp, "runs:", d.get("runs_total"))
