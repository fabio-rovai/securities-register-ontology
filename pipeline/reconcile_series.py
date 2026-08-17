"""Reconcile the two halves of the series<->LEI crosswalk that exist on
opposite sides of the register boundary:

  LEFT:  GLEIF golden copy RA000665 records (LEI -> registeredAs = EDGAR S-id)
  RIGHT: N-PORT FUND_REPORTED_INFO (SERIES_ID -> SERIES_LEI, reported to SEC)
  BASE:  SEC investment company series and class register (which series exist;
         the register itself publishes no LEI column at all)

Outputs reports/series_reconciliation.json.
"""
import csv, json, os, re
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "..")
R = lambda n: os.path.join(BASE, "reports", n)
S_RE = re.compile(r"^S\d{9}$")

with open(R("gleif_edgar_records.json")) as f:
    gleif = json.load(f)
with open(R("nport_series_lei.json")) as f:
    nport = json.load(f)

# the SEC's own series register
register_series = set()
with open(os.path.join(BASE, "data", "ic_series_class_2026.csv"),
          encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        sid = (row.get("Series ID") or "").strip()
        if S_RE.match(sid):
            register_series.add(sid)

# left map: S-id -> set of ISSUED/any LEIs claiming it at GLEIF
left = {}
fmt = Counter()
for rec in gleif:
    ra = rec["registeredAs"].strip()
    if S_RE.match(ra):
        fmt["series"] += 1
        left.setdefault(ra, []).append(rec)
    elif re.match(r"^\d{1,10}$", ra):
        fmt["cik"] += 1
    elif ra == "":
        fmt["empty"] += 1
    else:
        fmt["other"] += 1

pairs = {}
stats = Counter()
for sid, recs in left.items():
    issued = [r for r in recs if r["regStatus"] == "ISSUED"]
    rep = nport.get(sid)
    stats["gleif_series"] += 1
    if len(recs) > 1:
        stats["gleif_multiple_leis_per_series"] += 1
    if sid not in register_series:
        stats["gleif_sid_not_in_sec_series_register"] += 1
    if rep and rep.get("lei"):
        chosen = issued[0] if issued else recs[0]
        agree = any(r["lei"] == rep["lei"] for r in recs)
        pairs[sid] = {"gleif_lei": chosen["lei"], "nport_lei": rep["lei"],
                      "agree": agree, "n_gleif": len(recs),
                      "gleif_status": chosen["regStatus"],
                      "name": rep.get("name", "")}
        stats["compared"] += 1
        stats["agree" if agree else "disagree"] += 1
    else:
        stats["gleif_only"] += 1

nport_sids = {s for s, v in nport.items() if v.get("lei") and S_RE.match(s)}
stats["nport_series_with_lei"] = len(nport_sids)
stats["nport_only"] = len(nport_sids - set(left))
stats["sec_register_series_total"] = len(register_series)

disagreements = {s: v for s, v in pairs.items() if not v["agree"]}
summary = {"registeredAs_formats": dict(fmt), "stats": dict(stats),
           "disagreements": disagreements, "pairs": pairs}
with open(R("series_reconciliation.json"), "w") as f:
    json.dump(summary, f, indent=1)

print(json.dumps({"formats": dict(fmt), "stats": dict(stats)}, indent=1))
print("disagreements:", len(disagreements))
for s, v in list(disagreements.items())[:15]:
    print(" ", s, v["name"][:40], "gleif:", v["gleif_lei"], v["gleif_status"],
          "| nport:", v["nport_lei"])
