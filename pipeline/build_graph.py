"""Build the register-integrity graph as Turtle, emitted directly as text
(never via rdflib construction) and parse-verified afterwards.

Inputs: reports/*.json produced by the census scripts.
Output: data/graph.ttl (regenerable; not committed).

Every fact is an assertion, reconciliation, or coverage observation dated to
the harvest date. Entity URIs: ent:cik-<n>, ent:series-<SID>, ent:lei-<LEI>
(the last only when no SEC-side id is known for the GLEIF record).
"""
import csv, json, os, re, sys

BASE = os.path.join(os.path.dirname(__file__), "..")
R = lambda name: os.path.join(BASE, "reports", name)
HARVEST = "2026-08-17"

SEC_NS = "https://gov.tesseract.academy/def/securities#"
SCH = "https://gov.tesseract.academy/def/securities/scheme#"
ENT = "https://gov.tesseract.academy/def/securities/entity#"

def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def load(name, default=None):
    p = R(name)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return default

PHONE = re.compile(r"[()\-\s]*\d{3}[()\-\s.]+\d{3}[-\s.]+\d{4}|^\d{2,3}-\d-\d{4}-\d{4}$")
EIN = re.compile(r"^\d{2}-\d{7}")
ALPHA = re.compile(r"[A-Z]{3,}.*[ .,]")

def refine_reason(bucket, value):
    """Split 'malformed' into foreign_content vs malformed by shape of the junk.
    Populated N/A-style tokens are placeholders: the register published a
    value, and the value is a stand-in, not an identifier."""
    if bucket == "empty":
        return "placeholder"
    if bucket != "malformed":
        return bucket
    v = value.strip().upper()
    if PHONE.search(v) or EIN.match(v) or ALPHA.search(v):
        return "foreign_content"
    return "malformed"

def main():
    out = open(os.path.join(BASE, "data", "graph.ttl"), "w")
    w = out.write
    w(f"@prefix sec: <{SEC_NS}> .\n@prefix scheme: <{SCH}> .\n@prefix ent: <{ENT}> .\n")
    w("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n\n")

    # Registers
    for rid, label, op in [
        ("edgarEntityRegister", "EDGAR entity register (submissions API / bulk submissions file)", "SEC"),
        ("nportDataset", "Form N-PORT structured dataset 2026Q2", "SEC"),
        ("ncenDataset", "Form N-CEN structured dataset 2026Q2", "SEC"),
        ("seriesClassRegister", "SEC investment company series and class register 2026", "SEC"),
        ("gleifGoldenCopy", "GLEIF LEI golden copy 2026-08-17 08:00", "GLEIF"),
    ]:
        w(f'sec:{rid} a sec:Register ; rdfs:label "{esc(label)}" ; sec:operatedBy sec:{op} .\n')
    w('sec:SEC a sec:RegisterOperator ; rdfs:label "US Securities and Exchange Commission" .\n')
    w('sec:GLEIF a sec:RegisterOperator ; rdfs:label "Global Legal Entity Identifier Foundation" .\n\n')

    gleif_found = load("gleif_wanted_found.json", {})

    def lei_facets(norm_lei, conformant):
        """resolvesToLEIRecord + status facets for a conformant LEI value."""
        if not conformant or not norm_lei:
            return ""
        rec = gleif_found.get(norm_lei)
        if rec is None:
            return " ;\n    sec:resolvesToLEIRecord false"
        return (f" ;\n    sec:resolvesToLEIRecord true ;\n"
                f'    sec:leiRegistrationStatus "{esc(rec["regStatus"])}"')

    def emit_assertion(aid, register, entity, scheme, value, bucket, norm=None):
        conf = bucket == "valid"
        reason = refine_reason(bucket, value) if not conf else None
        w(f"ent:{aid} a sec:IdentifierAssertion ;\n")
        w(f"    sec:assertedBy sec:{register} ;\n")
        w(f"    sec:aboutEntity ent:{entity} ;\n")
        w(f"    sec:inScheme scheme:{scheme} ;\n")
        w(f'    sec:identifierValue "{esc(value)}" ;\n')
        w(f'    sec:assertedOn "{HARVEST}"^^xsd:date ;\n')
        w(f"    sec:schemeConformant {'true' if conf else 'false'}")
        if reason:
            w(f' ;\n    sec:nonConformanceReason "{reason}"')
        if scheme == "LEI":
            w(lei_facets(norm or value, conf))
        w(" .\n")

    counts = {"assertions": 0, "recons": 0, "coverage": 0, "entities": set()}

    def entity_node(eid, label=None, cls="RegisteredEntity"):
        if eid not in counts["entities"]:
            counts["entities"].add(eid)
            w(f"ent:{eid} a sec:{cls}")
            if label:
                w(f' ; rdfs:label "{esc(label)}"')
            w(" .\n")

    # 1. EDGAR entity-register lei field: ALL populated values, conformant or not
    pop = load("edgar_lei_populated.json", {})
    for cik, v in pop.items():
        eid = f"cik-{int(cik)}"
        entity_node(eid, v.get("name"))
        emit_assertion(f"a-edgar-{int(cik)}", "edgarEntityRegister", eid, "LEI",
                       v["lei"], v["bucket"], v["lei"].upper() if v["bucket"] == "valid" else None)
        counts["assertions"] += 1

    # 2. N-PORT registrant LEIs
    nport_cik = load("nport_cik_lei.json", {})
    for cik, v in nport_cik.items():
        if not v.get("lei"):
            continue
        eid = f"cik-{int(cik)}"
        entity_node(eid, v.get("name"))
        emit_assertion(f"a-nport-{int(cik)}", "nportDataset", eid, "LEI",
                       v["lei"], v["bucket"], v["lei"])
        counts["assertions"] += 1

    # 3. N-CEN registrant LEIs
    ncen_cik = load("ncen_cik_lei_crosswalk.json", {})
    for cik, v in ncen_cik.items():
        if not v.get("lei"):
            continue
        eid = f"cik-{int(cik)}"
        entity_node(eid, v.get("name"))
        emit_assertion(f"a-ncen-{int(cik)}", "ncenDataset", eid, "LEI",
                       v["lei"], v["bucket"], v["lei"])
        counts["assertions"] += 1

    # 4. N-PORT series LEIs
    series = load("nport_series_lei.json", {})
    for sid, v in series.items():
        if not v.get("lei") or not re.match(r"^S\d{9}$", sid):
            continue
        eid = f"series-{sid}"
        entity_node(eid, v.get("name"), "FundSeries")
        emit_assertion(f"a-nports-{sid}", "nportDataset", eid, "LEI",
                       v["lei"], v["bucket"], v["lei"])
        counts["assertions"] += 1

    # 5. GLEIF RA000665 reverse assertions: GLEIF asserts the EDGAR id for the LEI holder
    edgar_recs = load("gleif_edgar_records.json", [])
    S_RE = re.compile(r"^S\d{9}$")
    CIK_RE = re.compile(r"^\d{1,10}$")
    for r in edgar_recs:
        ra = r["registeredAs"].strip()
        lei = r["lei"]
        if S_RE.match(ra):
            eid, schm, bucket = f"series-{ra}", "SeriesID", "valid"
        elif CIK_RE.match(ra):
            eid, schm, bucket = f"cik-{int(ra)}", "CIK", "valid"
        else:
            eid, schm, bucket = f"lei-{lei}", ("SeriesID" if ra else "SeriesID"), "malformed" if ra else "empty"
            if not ra:
                continue  # counted in report; nothing to assert
        entity_node(eid, r.get("name"), "FundSeries" if schm == "SeriesID" else "RegisteredEntity")
        w(f"ent:a-gleif-{lei} a sec:IdentifierAssertion ;\n")
        w(f"    sec:assertedBy sec:gleifGoldenCopy ;\n")
        w(f"    sec:aboutEntity ent:{eid} ;\n")
        w(f"    sec:inScheme scheme:{schm} ;\n")
        w(f'    sec:identifierValue "{esc(ra)}" ;\n')
        w(f'    sec:assertedOn "{HARVEST}"^^xsd:date ;\n')
        w(f"    sec:schemeConformant {'true' if bucket == 'valid' else 'false'}")
        if bucket != "valid":
            w(f' ;\n    sec:nonConformanceReason "malformed"')
        w(f' ;\n    sec:gleifLEI "{lei}"')
        w(f' ;\n    sec:gleifRegStatus "{esc(r["regStatus"])}" .\n')
        counts["assertions"] += 1

    # 6. Reconciliations: series-level GLEIF vs N-PORT
    recon = load("series_reconciliation.json", {})
    for sid, v in recon.get("pairs", {}).items():
        oid = f"rec-series-{sid}"
        w(f"ent:{oid} a sec:ReconciliationObservation ;\n")
        w(f"    sec:leftAssertion ent:a-gleif-{v['gleif_lei']} ;\n")
        w(f"    sec:rightAssertion ent:a-nports-{sid} ;\n")
        w(f"    sec:agrees {'true' if v['agree'] else 'false'} ;\n")
        w(f'    sec:observedOn "{HARVEST}"^^xsd:date .\n')
        counts["recons"] += 1

    # 7. CIK-level reconciliation: N-PORT vs entity register (both populated)
    for cik, v in nport_cik.items():
        c = str(int(cik))
        e = {str(int(k)): x for k, x in pop.items()}.get(c)
        if not v.get("lei") or not e or e["bucket"] != "valid":
            continue
        agree = v["lei"] == e["lei"].upper()
        oid = f"rec-cik-{c}"
        w(f"ent:{oid} a sec:ReconciliationObservation ;\n")
        w(f"    sec:leftAssertion ent:a-nport-{c} ;\n")
        w(f"    sec:rightAssertion ent:a-edgar-{c} ;\n")
        w(f"    sec:agrees {'true' if agree else 'false'} ;\n")
        w(f'    sec:observedOn "{HARVEST}"^^xsd:date .\n')
        counts["recons"] += 1

    # 8. Coverage observations: SEC holds the LEI on a form surface, entity register silent
    pop_ciks = {str(int(k)) for k in pop}
    held = {}
    for cik, v in list(nport_cik.items()) + list(ncen_cik.items()):
        c = str(int(cik))
        if v.get("lei") and v["bucket"] == "valid":
            held.setdefault(c, v)
    for c, v in held.items():
        if c in pop_ciks:
            continue
        eid = f"cik-{c}"
        entity_node(eid, v.get("name"))
        oid = f"cov-{c}"
        w(f"ent:{oid} a sec:CoverageObservation ;\n")
        w(f"    sec:aboutEntity ent:{eid} ;\n")
        w(f'    sec:holdingSurface "N-PORT/N-CEN structured dataset" ;\n')
        w(f'    sec:silentSurface "EDGAR entity register lei field" ;\n')
        w(f'    sec:observedOn "{HARVEST}"^^xsd:date .\n')
        counts["coverage"] += 1

    out.close()
    print("assertions:", counts["assertions"], "recons:", counts["recons"],
          "coverage:", counts["coverage"], "entities:", len(counts["entities"]))


if __name__ == "__main__":
    main()
