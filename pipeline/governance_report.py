"""Dual-computation gate. Every headline number is computed set-based from the
census JSONs AND independently via SPARQL/SHACL over the graph. Any
disagreement exits non-zero. Known-answer cases are asserted first.

Usage: python3 pipeline/governance_report.py [--skip-shacl]
"""
import json, os, sys, re

BASE = os.path.join(os.path.dirname(__file__), "..")
R = lambda n: json.load(open(os.path.join(BASE, "reports", n)))
sys.path.insert(0, os.path.dirname(__file__))
from lei_util import classify_lei

failures = []

def check(label, a, b):
    ok = a == b
    print(f"{'OK ' if ok else 'FAIL'} {label}: set-based={a} graph={b}")
    if not ok:
        failures.append(label)

# ---------- known-answer cases ----------
found = R("gleif_wanted_found.json")
apple = found.get("HWUPKR0MPOU8FGXBT394")
assert apple and apple["regStatus"] == "ISSUED" and "APPLE" in apple["name"].upper(), \
    f"known-answer Apple failed: {apple}"
pop = R("edgar_lei_populated.json")
assert "320193" not in pop and "0000320193" not in pop, "Apple must be absent from populated set"
usb = pop.get("36104")
assert usb and usb["bucket"] == "valid" and usb["lei"] == "N1GZ7BBF3NP8GI976H15", \
    f"known-answer US Bancorp failed: {usb}"
print("known-answer cases pass (Apple ISSUED@GLEIF/absent@EDGAR; US Bancorp present+valid)")

# ---------- set-based ----------
from build_graph import refine_reason  # same classification the graph uses

sub = R("submissions_census.json")["stats"]
edgar_by_reason = {}
for v in pop.values():
    r = "valid" if v["bucket"] == "valid" else refine_reason(v["bucket"], v["lei"])
    edgar_by_reason[r] = edgar_by_reason.get(r, 0) + 1

nport_cik = {k: v for k, v in R("nport_cik_lei.json").items() if v.get("lei")}
ncen_cik = {k: v for k, v in R("ncen_cik_lei_crosswalk.json").items() if v.get("lei")}
series = {k: v for k, v in R("nport_series_lei.json").items()
          if v.get("lei") and re.match(r"^S\d{9}$", k)}
gleif_edgar = R("gleif_edgar_records.json")
gleif_nonempty = [r for r in gleif_edgar if r["registeredAs"].strip()]
recon = R("series_reconciliation.json")

set_assertions = (len(pop) + len(nport_cik) + len(ncen_cik) + len(series)
                  + len(gleif_nonempty))
set_recons = recon["stats"]["compared"]
pop_ciks = {str(int(k)) for k in pop}
held = {}
for cik, v in list(nport_cik.items()) + list(ncen_cik.items()):
    if v["bucket"] == "valid":
        held.setdefault(str(int(cik)), v)
set_coverage = sum(1 for c in held if c not in pop_ciks)
set_series_disagree = recon["stats"]["disagree"]

# CIK-level: N-PORT vs entity register
cik_pairs = cik_disagree = 0
pop_norm = {str(int(k)): v for k, v in pop.items()}
for cik, v in nport_cik.items():
    e = pop_norm.get(str(int(cik)))
    if e and e["bucket"] == "valid":
        cik_pairs += 1
        if v["lei"] != e["lei"].upper():
            cik_disagree += 1

# SEC-asserted LEI statuses (valid values on SEC surfaces)
sec_valid_leis = set()
for src in (pop, nport_cik, ncen_cik, series):
    for v in src.values():
        if v.get("bucket") == "valid" and v.get("lei"):
            sec_valid_leis.add(v["lei"].upper())
status = {"missing": 0}
for lei in sec_valid_leis:
    rec = found.get(lei)
    if rec is None:
        status["missing"] += 1
    else:
        status[rec["regStatus"]] = status.get(rec["regStatus"], 0) + 1

summary = {
    "edgar_members_main": sub["members_main"],
    "edgar_lei_populated": sub["lei_populated"],
    "edgar_by_reason": edgar_by_reason,
    "listed_total": sub["listed_total"], "listed_populated": sub["listed_populated"],
    "form_held_cik_pairs": len(set(list(nport_cik) + list(ncen_cik))),
    "coverage_held_not_surfaced": set_coverage,
    "series_pairs_compared": set_recons, "series_disagree": set_series_disagree,
    "cik_pairs_compared": cik_pairs, "cik_disagree": cik_disagree,
    "sec_asserted_distinct_valid_leis": len(sec_valid_leis),
    "sec_asserted_lei_status_at_gleif": status,
    "gleif_edgar_records": len(gleif_edgar),
    "isin_census": R("isin_census.json"),
}
with open(os.path.join(BASE, "reports", "GOVERNANCE_SUMMARY.json"), "w") as f:
    json.dump(summary, f, indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "isin_census"}, indent=1))

# ---------- graph-based ----------
import rdflib
g = rdflib.Graph()
g.parse(os.path.join(BASE, "data", "graph.ttl"), format="turtle")
SEC = "https://gov.tesseract.academy/def/securities#"

def q1(query):
    return int(list(g.query(query))[0][0].toPython())

P = f"PREFIX sec: <{SEC}>\n"
check("total assertions", set_assertions,
      q1(P + "SELECT (COUNT(?a) AS ?n) WHERE { ?a a sec:IdentifierAssertion }"))
check("edgar populated assertions", len(pop),
      q1(P + "SELECT (COUNT(?a) AS ?n) WHERE { ?a a sec:IdentifierAssertion ; sec:assertedBy sec:edgarEntityRegister }"))
for reason, n in sorted(edgar_by_reason.items()):
    if reason == "valid":
        check("edgar valid", n, q1(P + "SELECT (COUNT(?a) AS ?n) WHERE { ?a sec:assertedBy sec:edgarEntityRegister ; sec:schemeConformant true }"))
    else:
        check(f"edgar reason {reason}", n,
              q1(P + f'SELECT (COUNT(?a) AS ?n) WHERE {{ ?a sec:assertedBy sec:edgarEntityRegister ; sec:nonConformanceReason "{reason}" }}'))
check("reconciliations", set_recons + cik_pairs,
      q1(P + "SELECT (COUNT(?o) AS ?n) WHERE { ?o a sec:ReconciliationObservation }"))
check("disagreements", set_series_disagree + cik_disagree,
      q1(P + "SELECT (COUNT(?o) AS ?n) WHERE { ?o a sec:ReconciliationObservation ; sec:agrees false }"))
check("coverage observations", set_coverage,
      q1(P + "SELECT (COUNT(?o) AS ?n) WHERE { ?o a sec:CoverageObservation }"))
lapsed_graph = q1(P + 'SELECT (COUNT(?a) AS ?n) WHERE { ?a sec:leiRegistrationStatus "LAPSED" }')
lapsed_set = 0
for src in (pop, nport_cik, ncen_cik, series):
    for v in src.values():
        if v.get("bucket") == "valid" and found.get((v.get("lei") or "").upper(), {}).get("regStatus") == "LAPSED":
            lapsed_set += 1
check("LAPSED on SEC-asserted assertions", lapsed_set, lapsed_graph)

# ---------- SHACL ----------
# pyshacl evaluates sh:sparql constraints once PER FOCUS NODE, which is
# quadratic at 43k assertions (measured: >70 min, killed). Each of our sparql
# shapes is a self-contained SELECT over the graph, so executing each query
# ONCE over the data graph yields the identical violation set. The shape
# files remain the normative artifacts; this is an execution strategy, the
# same one the open-ontologies engine uses. Layer 1 property shapes are
# checked with equivalent single-pass queries for required properties.
if "--skip-shacl" not in sys.argv:
    import time
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    def run_layer(layer):
        sg = rdflib.Graph()
        sg.parse(os.path.join(BASE, "shacl", layer), format="turtle")
        total = 0
        t = time.time()
        for s, p, o in sg.triples((None, SH.select, None)):
            q = str(o).replace("$this", "?this")
            total += len(list(g.query(q)))
        # property-shape minCount checks, single-pass
        for shape in sg.subjects(rdflib.RDF.type, SH.NodeShape):
            tc = sg.value(shape, SH.targetClass)
            if tc is None:
                continue
            for pshape in sg.objects(shape, SH.property):
                path = sg.value(pshape, SH.path)
                minc = sg.value(pshape, SH.minCount)
                if path is None or minc is None or int(minc) < 1:
                    continue
                q = f"""SELECT ?x WHERE {{ ?x a <{tc}> . FILTER NOT EXISTS {{ ?x <{path}> ?v }} }}"""
                total += len(list(g.query(q)))
        return total, round(time.time() - t, 1)

    n1, t1 = run_layer("layer1-structural.ttl")
    print(f"SHACL layer1 (single-pass): violations={n1} ({t1}s)")
    if n1 != 0:
        failures.append("layer1 must be clean")

    n2, t2 = run_layer("layer2-conformance.ttl")
    expected2 = sum(n for r, n in edgar_by_reason.items() if r != "valid")
    expected2 += sum(1 for src_ in (nport_cik, ncen_cik, series)
                     for v in src_.values() if v["bucket"] != "valid")
    print(f"SHACL layer2 (single-pass): violations={n2} ({t2}s)")
    check("layer2 violations == non-conformant SEC assertions", expected2, n2)

    n3, t3 = run_layer("layer3-crossregister.ttl")
    dangling = q1(P + "SELECT (COUNT(?a) AS ?n) WHERE { ?a sec:schemeConformant true ; sec:resolvesToLEIRecord false }")
    retired = q1(P + 'SELECT (COUNT(?a) AS ?n) WHERE { ?a sec:leiRegistrationStatus ?s . FILTER(?s = "RETIRED" || ?s = "ANNULLED" || ?s = "MERGED" || ?s = "DUPLICATE") }')
    expected3 = dangling + lapsed_graph + retired + (set_series_disagree + cik_disagree) + set_coverage
    print(f"SHACL layer3 (single-pass): violations={n3} ({t3}s)")
    check("layer3 violations == sum of defect classes", expected3, n3)

print()
if failures:
    print("GOVERNANCE FAILURES:", failures)
    sys.exit(1)
print("ALL CROSS-CHECKS AGREE")
