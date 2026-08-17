"""Census every LEI column in the N-CEN 2026Q2 structured dataset.
Outputs reports/ncen_census.json: per-table per-column buckets, plus the
registrant-level CIK->LEI crosswalk the SEC holds but does not publish."""
import csv, json, sys, glob, os

sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_lei

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "ncen")
OUT = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(OUT, exist_ok=True)
csv.field_size_limit(10_000_000)

result, crosswalk = {}, {}
for path in sorted(glob.glob(os.path.join(DATA, "*.tsv"))):
    table = os.path.basename(path)[:-4]
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        lei_cols = [c for c in (rdr.fieldnames or []) if "LEI" in c.upper()]
        if not lei_cols:
            continue
        counts = {c: {"empty": 0, "placeholder": 0, "malformed": 0,
                      "bad_checksum": 0, "valid": 0, "rows": 0,
                      "bad_values": []} for c in lei_cols}
        for row in rdr:
            for c in lei_cols:
                bucket, norm = classify_lei(row.get(c))
                counts[c][bucket] += 1
                counts[c]["rows"] += 1
                if bucket in ("malformed", "bad_checksum", "placeholder") \
                        and len(counts[c]["bad_values"]) < 25:
                    counts[c]["bad_values"].append(row.get(c))
            if table == "REGISTRANT":
                cik = (row.get("CIK") or row.get("REGISTRANT_CIK") or "").strip()
                bucket, norm = classify_lei(row.get("REGISTRANT_LEI") or row.get("LEI"))
                if cik:
                    crosswalk[cik] = {"lei": norm, "bucket": bucket,
                                      "name": row.get("REGISTRANT_NAME", "")}
        result[table] = counts

with open(os.path.join(OUT, "ncen_census.json"), "w") as f:
    json.dump({"tables": result, "registrant_crosswalk_size": len(crosswalk)}, f, indent=1)
with open(os.path.join(OUT, "ncen_cik_lei_crosswalk.json"), "w") as f:
    json.dump(crosswalk, f, indent=1)

total = {"empty": 0, "placeholder": 0, "malformed": 0, "bad_checksum": 0, "valid": 0, "rows": 0}
for t, cols in result.items():
    for c, k in cols.items():
        for b in total:
            total[b] += k[b]
print("TOTAL over all N-CEN LEI columns:", total)
print("registrant CIK->LEI pairs:", len(crosswalk))
valid_xw = sum(1 for v in crosswalk.values() if v["bucket"] == "valid")
print("registrants with VALID self-reported LEI:", valid_xw)
for t, cols in result.items():
    for c, k in cols.items():
        if k["malformed"] or k["bad_checksum"] or k["placeholder"]:
            print(f"{t}.{c}: rows={k['rows']} valid={k['valid']} empty={k['empty']} "
                  f"malformed={k['malformed']} bad_checksum={k['bad_checksum']} "
                  f"placeholder={k['placeholder']} sample={k['bad_values'][:5]}")
