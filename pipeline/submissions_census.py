"""Census the `lei` field across every entity in EDGAR's bulk submissions file.

Fast path: regex over each zip member's raw bytes (the top-level scalar fields
sit before the huge `filings` object). Correctness gate: a full json.loads
cross-check on a random sample; the script exits non-zero if the two methods
ever disagree on a sampled member.

Outputs reports/submissions_census.json + reports/edgar_lei_populated.json.
"""
import io, json, os, random, re, sys, zipfile

sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_lei

BASE = os.path.join(os.path.dirname(__file__), "..")
ZIP = os.path.join(BASE, "data", "submissions.zip")
OUT = os.path.join(BASE, "reports")
os.makedirs(OUT, exist_ok=True)

RE_LEI = re.compile(rb'"lei"\s*:\s*(null|"([^"]*)")')
RE_NAME = re.compile(rb'"name"\s*:\s*"([^"]*)"')
RE_CIK = re.compile(rb'"cik"\s*:\s*"?(\d+)"?')
RE_TYPE = re.compile(rb'"entityType"\s*:\s*"([^"]*)"')

random.seed(20260817)

listed = set()
with open(os.path.join(BASE, "data", "company_tickers.json")) as f:
    for v in json.load(f).values():
        listed.add(int(v["cik_str"]))

ic_ciks = set()
with open(os.path.join(BASE, "data", "ic_series_class_2026.csv"), encoding="utf-8-sig") as f:
    import csv
    for row in csv.DictReader(f):
        try:
            ic_ciks.add(int(row["CIK Number"]))
        except (ValueError, KeyError):
            pass

stats = {
    "members_total": 0, "members_main": 0, "lei_field_absent": 0,
    "lei_null_or_empty": 0, "lei_populated": 0,
    "listed_total": 0, "listed_populated": 0,
    "ic_total": 0, "ic_populated": 0,
    "sample_checked": 0, "sample_mismatch": 0,
}
populated = {}
bad_lei = []

with zipfile.ZipFile(ZIP) as z:
    names = z.namelist()
    stats["members_total"] = len(names)
    for n in names:
        if "-submissions-" in n or not n.endswith(".json"):
            continue  # paging files carry only older filing lists
        stats["members_main"] += 1
        raw = z.read(n)
        m = RE_LEI.search(raw)
        cik_m = RE_CIK.search(raw)
        cik = int(cik_m.group(1)) if cik_m else None
        lei_val = None
        if m is None:
            stats["lei_field_absent"] += 1
        elif m.group(1) == b"null" or m.group(2) == b"":
            stats["lei_null_or_empty"] += 1
        else:
            lei_val = m.group(2).decode()
            stats["lei_populated"] += 1
            nm = RE_NAME.search(raw)
            bucket, norm = classify_lei(lei_val)
            populated[str(cik)] = {
                "lei": lei_val, "bucket": bucket,
                "name": nm.group(1).decode() if nm else "",
            }
            if bucket != "valid":
                bad_lei.append({"cik": cik, "lei": lei_val, "bucket": bucket})
        if cik in listed:
            stats["listed_total"] += 1
            if lei_val:
                stats["listed_populated"] += 1
        if cik in ic_ciks:
            stats["ic_total"] += 1
            if lei_val:
                stats["ic_populated"] += 1
        # dual-computation gate on ~1/500 sample
        if random.random() < 0.002:
            stats["sample_checked"] += 1
            d = json.loads(raw)
            true_lei = d.get("lei") or None
            regex_lei = lei_val
            if (true_lei or None) != (regex_lei or None):
                stats["sample_mismatch"] += 1
                print("MISMATCH", n, repr(true_lei), repr(regex_lei))

with open(os.path.join(OUT, "submissions_census.json"), "w") as f:
    json.dump({"stats": stats, "bad_lei": bad_lei}, f, indent=1)
with open(os.path.join(OUT, "edgar_lei_populated.json"), "w") as f:
    json.dump(populated, f, indent=1)

print(json.dumps(stats, indent=1))
if stats["sample_mismatch"]:
    sys.exit(1)
