# Securities Entity Register Ontology

An open OWL 2 + SKOS + SHACL model for register integrity in US securities
entity identification, tested against the entire public record on the day the
Financial Data Transparency Act joint standards take effect territory: the
EDGAR entity register (981,355 entities), the GLEIF LEI golden copy
(3,404,295 records), the open ISIN-LEI mapping (9,135,428 rows), and the
SEC's N-PORT and N-CEN structured datasets for 2026 Q2.

## The finding in one sentence

On 1 October 2026 the Legal Entity Identifier becomes the joint entity
standard for nine US financial agencies under 91 FR 38246, and the SEC's
entity register has an LEI field that is populated for 773 of 981,355
entities, contains telephone numbers and entity names where LEIs should be,
and disagrees with the LEIs the same agency collects on its own forms.

Headline numbers (all reproducible from `pipeline/`, all dual-computed):

- 773 of 981,355 EDGAR entity records carry a populated `lei` field
  (0.079 percent). 667 of the 773 are valid LEIs. The rest include phone
  numbers, IRS EINs, entity names, "N/A", and values that fail the ISO 7064
  check digits.
- 1,973 fund registrants reported their LEI to the SEC on Forms N-PORT and
  N-CEN in a single quarter; the entity register surfaces 12 of them.
- GLEIF publishes an EDGAR-identifier crosswalk for 27,705 LEI records
  (series IDs and CIKs in `registeredAs`); no SEC surface publishes the
  reverse, and the SEC's series and class register has no LEI column.
- Where the two sides of the series crosswalk can be compared (12,604
  series), 100 fund series carry two different LEIs across the register
  boundary, including checksum-detectable single-character substitutions
  and cyclically swapped sibling ETFs.
- 56.6 percent of all US LEI records are LAPSED at GLEIF (202,698 of
  358,294).

Full numbers, method, specimens, and the honest not-obtained list:
[docs/BUILD_REPORT.md](docs/BUILD_REPORT.md).

## Why an ontology

Because every one of these defects is invisible to schema validation on any
single register and only becomes computable when identity is modelled as
what it actually is in the public record: a dated claim by a named register.
The ontology reifies each published value as an `IdentifierAssertion` with
`schemeConformant`, `nonConformanceReason`, `resolvesToLEIRecord`, and
`leiRegistrationStatus` facets; cross-register comparisons are first-class
`ReconciliationObservation` nodes; and a register holding an identifier on
one surface while leaving another empty is a recorded
`CoverageObservation`, because silence is a position.

The SKOS scheme registry (`ontology/schemes.ttl`) declares each identifier
scheme's length, charset, and check-digit algorithm as data; the pipeline
validates every value against the rules its claimed scheme declares, and the
SHACL layers turn each defect class into one shape, so the validation report
is the findings table.

## Layout

```
ontology/   OWL core + SKOS scheme registry
shacl/      layer1 structural, layer2 scheme conformance, layer3 cross-register
pipeline/   download + census + reconciliation + graph build + governance gate
queries/    verified SPARQL queries (q1-q6)
reports/    committed summary JSONs (aggregates only)
docs/       BUILD_REPORT.md
tests/      offline unit tests (known-answer identifiers, parse checks)
```

Bulk register data is never committed; `pipeline/download.sh` regenerates
everything (about 2.5 GB). The graph (526,098 triples) is emitted directly
as Turtle text and parse-verified, then gated by
`pipeline/governance_report.py`, which recomputes every headline set-based
and via SPARQL/SHACL and exits non-zero on any disagreement.

## Worked example

Who is CIK 892538? The entity register says its LEI is
`549300E40BQMHI2LOX26`. GLEIF says that LEI is SunAmerica Asset Management,
LLC, the fund's adviser. Form N-PORT, filed by the fund itself, says
`549300YDIAXUNCUXFM44`, which GLEIF registers as SunAmerica Series Trust
against exactly this CIK. Run it yourself:

```
python3 -c "
import rdflib
g = rdflib.Graph(); g.parse('data/graph.ttl', format='turtle')
q = open('queries/q3_disagreements.rq').read()
for row in g.query(q):
    print(row)
"
```

## Licence

Code MIT; ontology and documentation CC BY 4.0. EDGAR data is US Government
work; GLEIF data is CC0. CUSIP values observed inside SEC filings are
analysed statistically and never redistributed.

## Contact

Built by [Fabio Rovai](https://gov.tesseract.academy) (Kampakis and Co Ltd,
t/a The Tesseract Academy). If your register, fund complex, or reporting
pipeline embeds identifiers you do not control and you want the same audit
run against it, write to fabio@thetesseractacademy.com with the register
name; a scoped diagnostic of one register boundary is a one-week engagement.
