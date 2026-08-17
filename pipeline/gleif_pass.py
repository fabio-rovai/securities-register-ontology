"""Single streaming pass over the GLEIF lei2 golden copy (3.4M records).

Collects:
  1. Every RA000665 (EDGAR) record -> the reverse crosswalk GLEIF holds
     (registeredAs format classes: S-series id, numeric CIK, other).
  2. Status/country aggregates (US population, global).
  3. Full records for every LEI referenced by N-CEN (and, later, N-PORT):
     wanted-set join for lapsed/retired/dangling classification.
Outputs reports/gleif_pass.json + reports/gleif_edgar_records.json.
"""
import csv, io, json, os, re, sys, zipfile
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "reports")
csv.field_size_limit(10_000_000)

wanted = set()
# every populated value in the EDGAR entity register (valid or not; uppercased)
pop_path = os.path.join(OUT := os.path.join(BASE, "reports"), "edgar_lei_populated.json")
if os.path.exists(pop_path):
    with open(pop_path) as f:
        for v in json.load(f).values():
            if v.get("lei"):
                wanted.add(str(v["lei"]).strip().upper())
ncen_path = os.path.join(OUT, "ncen_census.json")
xw_path = os.path.join(OUT, "ncen_cik_lei_crosswalk.json")
if os.path.exists(xw_path):
    with open(xw_path) as f:
        for v in json.load(f).values():
            if v.get("lei"):
                wanted.add(v["lei"])
# every distinct LEI value seen anywhere in N-CEN tables
import glob
sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_lei
for path in glob.glob(os.path.join(BASE, "data", "ncen", "*.tsv")):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        lei_cols = [c for c in (rdr.fieldnames or []) if "LEI" in c.upper()]
        if not lei_cols:
            continue
        for row in rdr:
            for c in lei_cols:
                b, norm = classify_lei(row.get(c))
                if norm:
                    wanted.add(norm)
# optional: N-PORT wanted set produced by nport_census.py first pass
np_wanted = os.path.join(OUT, "nport_wanted_leis.json")
if os.path.exists(np_wanted):
    with open(np_wanted) as f:
        wanted.update(json.load(f))
print("wanted LEI set:", len(wanted))

S_RE = re.compile(r"^S\d{9}$")
CIK_RE = re.compile(r"^\d{1,10}$")

edgar_records = []
found = {}
by_country = Counter()
by_status_us = Counter()
total = 0

with zipfile.ZipFile(os.path.join(BASE, "data", "lei2.csv.zip")) as z:
    with z.open(z.namelist()[0]) as raw:
        rdr = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        header = next(rdr)
        idx = {c.strip('"'): i for i, c in enumerate(header)}
        I_LEI = 0
        I_NAME = idx["Entity.LegalName"]
        I_CTRY = idx["Entity.LegalAddress.Country"]
        I_RA = idx["Entity.RegistrationAuthority.RegistrationAuthorityID"]
        I_RAE = idx["Entity.RegistrationAuthority.RegistrationAuthorityEntityID"]
        I_CAT = idx["Entity.EntityCategory"]
        I_ESTAT = idx["Entity.EntityStatus"]
        I_RSTAT = idx["Registration.RegistrationStatus"]
        for row in rdr:
            total += 1
            ctry = row[I_CTRY]
            by_country[ctry] += 1
            if ctry == "US":
                by_status_us[row[I_RSTAT]] += 1
            if row[I_RA] == "RA000665":
                edgar_records.append({
                    "lei": row[I_LEI], "name": row[I_NAME],
                    "registeredAs": row[I_RAE], "country": ctry,
                    "category": row[I_CAT], "entityStatus": row[I_ESTAT],
                    "regStatus": row[I_RSTAT],
                })
            lei = row[I_LEI]
            if lei in wanted:
                found[lei] = {"name": row[I_NAME], "country": ctry,
                              "entityStatus": row[I_ESTAT],
                              "regStatus": row[I_RSTAT],
                              "ra": row[I_RA], "registeredAs": row[I_RAE]}

fmt = Counter()
for r in edgar_records:
    ra = r["registeredAs"].strip()
    if S_RE.match(ra):
        fmt["series_id"] += 1
    elif CIK_RE.match(ra):
        fmt["cik_numeric"] += 1
    elif ra == "":
        fmt["empty"] += 1
    else:
        fmt["other"] += 1

dangling = sorted(wanted - set(found))
summary = {
    "total_records": total,
    "us_records": by_country["US"],
    "us_by_regstatus": dict(by_status_us),
    "top_countries": by_country.most_common(10),
    "edgar_ra_records": len(edgar_records),
    "edgar_registeredAs_formats": dict(fmt),
    "wanted_set": len(wanted),
    "wanted_found": len(found),
    "wanted_dangling": len(dangling),
    "dangling_sample": dangling[:50],
}
with open(os.path.join(OUT, "gleif_pass.json"), "w") as f:
    json.dump(summary, f, indent=1)
with open(os.path.join(OUT, "gleif_edgar_records.json"), "w") as f:
    json.dump(edgar_records, f, indent=1)
with open(os.path.join(OUT, "gleif_wanted_found.json"), "w") as f:
    json.dump(found, f, indent=1)
print(json.dumps(summary, indent=1)[:2000])
