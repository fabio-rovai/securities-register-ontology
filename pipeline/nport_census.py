"""Census identifier quality in the N-PORT 2026Q2 structured dataset (streamed
from the zip; FUND_REPORTED_HOLDING alone is 910MB).

Outputs:
  reports/nport_census.json          per-table identifier buckets
  reports/nport_series_lei.json      SERIES_ID -> SERIES_LEI as reported to SEC
  reports/nport_cik_lei.json         registrant CIK -> LEI as reported to SEC
  reports/nport_wanted_leis.json     every distinct LEI value (for gleif_pass)
"""
import csv, io, json, os, sys, zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_lei, classify_isin, classify_cusip

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "reports")
os.makedirs(OUT, exist_ok=True)
csv.field_size_limit(10_000_000)

Z = zipfile.ZipFile(os.path.join(BASE, "data", "2026q2_nport.zip"))

def stream(table):
    with Z.open(table) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8",
                                                   errors="replace", newline=""),
                                  delimiter="\t")

def bucket_counter():
    return Counter(rows=0)

census = {}
wanted = set()
series_lei = {}
cik_lei = {}

# 1. REGISTRANT: CIK -> LEI
c = Counter()
for row in stream("REGISTRANT.tsv"):
    b, norm = classify_lei(row.get("LEI"))
    c[b] += 1; c["rows"] += 1
    if norm:
        wanted.add(norm)
    cik = (row.get("CIK") or "").strip()
    if cik and cik not in cik_lei:
        cik_lei[cik] = {"lei": norm, "bucket": b,
                        "name": row.get("REGISTRANT_NAME", "")}
census["REGISTRANT.LEI"] = dict(c)

# 2. FUND_REPORTED_INFO: SERIES_ID -> SERIES_LEI
c = Counter()
for row in stream("FUND_REPORTED_INFO.tsv"):
    b, norm = classify_lei(row.get("SERIES_LEI"))
    c[b] += 1; c["rows"] += 1
    if norm:
        wanted.add(norm)
    sid = (row.get("SERIES_ID") or "").strip()
    if sid:
        prev = series_lei.get(sid)
        if prev and norm and prev["lei"] and prev["lei"] != norm:
            prev.setdefault("conflicts", []).append(norm)
        elif not prev:
            series_lei[sid] = {"lei": norm, "bucket": b,
                               "name": row.get("SERIES_NAME", "")}
census["FUND_REPORTED_INFO.SERIES_LEI"] = dict(c)

# 3. small LEI tables
for table, col in [("DERIVATIVE_COUNTERPARTY.tsv", "DERIVATIVE_COUNTERPARTY_LEI"),
                   ("BORROWER.tsv", "LEI")]:
    c = Counter()
    bad = []
    for row in stream(table):
        b, norm = classify_lei(row.get(col))
        c[b] += 1; c["rows"] += 1
        if norm:
            wanted.add(norm)
        if b in ("malformed", "bad_checksum", "placeholder") and len(bad) < 20:
            bad.append(row.get(col))
    census[f"{table[:-4]}.{col}"] = dict(c, bad_sample=bad)

# 4. FUND_REPORTED_HOLDING: ISSUER_LEI + ISSUER_CUSIP (910MB)
c_lei, c_cusip = Counter(), Counter()
bad_lei_sample = []
for row in stream("FUND_REPORTED_HOLDING.tsv"):
    b, norm = classify_lei(row.get("ISSUER_LEI"))
    c_lei[b] += 1; c_lei["rows"] += 1
    if norm:
        wanted.add(norm)
    if b in ("malformed", "bad_checksum", "placeholder") and len(bad_lei_sample) < 30:
        bad_lei_sample.append(row.get("ISSUER_LEI"))
    b2, _ = classify_cusip(row.get("ISSUER_CUSIP"))
    c_cusip[b2] += 1; c_cusip["rows"] += 1
census["FUND_REPORTED_HOLDING.ISSUER_LEI"] = dict(c_lei, bad_sample=bad_lei_sample)
census["FUND_REPORTED_HOLDING.ISSUER_CUSIP"] = dict(c_cusip)

# 5. IDENTIFIERS: ISIN
c = Counter()
bad_isin = []
for row in stream("IDENTIFIERS.tsv"):
    b, _ = classify_isin(row.get("IDENTIFIER_ISIN"))
    c[b] += 1; c["rows"] += 1
    if b in ("malformed", "bad_checksum") and len(bad_isin) < 20:
        bad_isin.append(row.get("IDENTIFIER_ISIN"))
census["IDENTIFIERS.IDENTIFIER_ISIN"] = dict(c, bad_sample=bad_isin)

with open(os.path.join(OUT, "nport_census.json"), "w") as f:
    json.dump(census, f, indent=1)
with open(os.path.join(OUT, "nport_series_lei.json"), "w") as f:
    json.dump(series_lei, f, indent=1)
with open(os.path.join(OUT, "nport_cik_lei.json"), "w") as f:
    json.dump(cik_lei, f, indent=1)
with open(os.path.join(OUT, "nport_wanted_leis.json"), "w") as f:
    json.dump(sorted(wanted), f)

print(json.dumps({k: {b: n for b, n in v.items() if b != "bad_sample"}
                  for k, v in census.items()}, indent=1))
print("series with reported LEI:", sum(1 for v in series_lei.values() if v["lei"]),
      "of", len(series_lei))
print("registrant CIKs:", len(cik_lei),
      "with LEI:", sum(1 for v in cik_lei.values() if v["lei"]))
print("wanted LEIs:", len(wanted))
