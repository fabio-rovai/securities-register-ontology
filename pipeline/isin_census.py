"""Full census of GLEIF's daily ISIN-LEI mapping file: rows, distinct
LEIs/ISINs, ISIN prefix (country) histogram. The US share is the finding: the
US NNA (CUSIP Global Services) barely contributes to the open mapping."""
import csv, io, json, os, sys, zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_isin, classify_lei

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "reports")

rows = 0
bad_isin = Counter()
bad_lei = Counter()
prefix = Counter()
leis = set()
us_leis = set()

with zipfile.ZipFile(os.path.join(BASE, "data", "isin-lei.zip")) as z:
    name = z.namelist()[0]
    with z.open(name) as raw:
        rdr = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        header = next(rdr)
        for row in rdr:
            rows += 1
            lei, isin = row[0].strip(), row[1].strip()
            b, norm = classify_isin(isin)
            bad_isin[b] += 1
            bl, lnorm = classify_lei(lei)
            bad_lei[bl] += 1
            if norm:
                prefix[norm[:2]] += 1
                if lnorm:
                    leis.add(lnorm)
                    if norm.startswith("US"):
                        us_leis.add(lnorm)

summary = {
    "file": name,
    "rows": rows,
    "distinct_leis": len(leis),
    "distinct_leis_with_us_isin": len(us_leis),
    "isin_buckets": dict(bad_isin),
    "lei_buckets": dict(bad_lei),
    "top20_prefixes": prefix.most_common(20),
    "us_rows": prefix["US"],
    "us_share_pct": round(100 * prefix["US"] / rows, 2) if rows else None,
}
with open(os.path.join(OUT, "isin_census.json"), "w") as f:
    json.dump(summary, f, indent=1)
print(json.dumps(summary, indent=1))
