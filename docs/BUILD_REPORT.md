# Build report: Securities Entity Register Ontology, 17 August 2026

This report records exactly what was fetched, what was computed, and what
could not be obtained. Every number below is produced by a script in
`pipeline/` and re-derived a second way by `pipeline/governance_report.py`,
which exits non-zero if the two computations ever disagree.

## Sources fetched (all keyless, all on 17 August 2026)

| Source | File | Size | Licence |
|---|---|---|---|
| EDGAR bulk submissions (entity register) | `submissions.zip`, last modified 15 Aug 2026 | 1,558,343,702 bytes, 986,703 members | US Government work, public domain |
| GLEIF golden copy lei2, 2026-08-17 16:00 publish | `lei2.csv.zip` | 499,272,552 bytes, 3,404,295 records | CC0 |
| GLEIF ISIN-LEI mapping, 2026-08-17 07:15 | `isin-lei.zip` | 32,121,021 bytes, 9,135,428 rows | CC0 |
| SEC Form N-PORT structured dataset 2026 Q2 | `2026q2_nport.zip` | 440,699,889 bytes | US Government work |
| SEC Form N-CEN structured dataset 2026 Q2 | `2026q2_ncen.zip` | 8,404,110 bytes | US Government work |
| SEC investment company series and class register 2026 | `investment-company-series-class-2026.csv` | 43,123 class rows, 19,340 distinct series | US Government work |
| SEC company_tickers.json (listed filers) | | 10,391 entries | US Government work |
| GLEIF registration authorities code list (API) | | 1,071 RA codes | CC0 |

Download notes: the GLEIF golden-copy and ISIN-LEI endpoints do not support
HTTP range resume; `pipeline/download.sh` retries from scratch until the
archive tests clean. EDGAR requires a User-Agent header identifying the
requester; the header used is recorded in the script.

## Findings

### 1. The entity register's LEI field is 99.92 percent empty

The EDGAR bulk submissions file contains 981,355 main entity records. Every
record carries a top-level `lei` field. It is null or empty in 980,582 of
them and populated in 773 (0.079 percent). Among the 7,992 listed operating
companies present in the file (matched via company_tickers.json), 25 have a
populated LEI (0.31 percent). Apple, whose LEI `HWUPKR0MPOU8FGXBT394` has
been ISSUED at GLEIF, has a null `lei` field; so do Microsoft, JPMorgan, and
essentially every household-name filer. For comparison, the same golden copy
shows 358,294 US LEI records.

Method note: the census regex fast-path was cross-checked by fully parsing a
random 2,020-member sample with `json.loads`; zero disagreements
(`submissions_census.py`, seeded sample).

### 2. What is in the field when it is populated

Of the 773 populated values: 667 are valid LEIs; 56 are malformed or foreign
content, including telephone numbers ("(646) 508-0022", "424-231-9100"),
IRS EINs ("33-4802710"), EDGAR file numbers, a state registry string
("US-CT.BER:3091043"), and entity names typed into the field ("DANGEROUS 7
SPV 2 LP", "WUWALLACEFAMILYTRUST"); 14 are 20-character LEI-shaped strings
that fail the ISO 7064 MOD 97-10 check digits; 35 are the literal string
"N/A"; 1 is all zeros. The register republishes all of this unvalidated.

### 3. The operator holds the crosswalk it does not publish

In 2026 Q2 alone, 1,947 fund registrants reported their LEI on Form N-PORT
and 460 on Form N-CEN (1,973 distinct CIKs). The entity register surfaces a
populated `lei` field for 12 of them. 1,954 coverage observations record
cases where the operator demonstrably holds a valid LEI for a CIK on one
publication surface while the entity register's field for the same CIK is
empty.

Where both surfaces are populated, they can disagree: for CIK 892538
(SunAmerica Series Trust) the entity register publishes
`549300E40BQMHI2LOX26`, which GLEIF identifies as SunAmerica Asset
Management, LLC, the trust's adviser. Form N-PORT reports
`549300YDIAXUNCUXFM44`, which GLEIF registers as SunAmerica Series Trust
against exactly this CIK (registeredAs 0000892538). The register carries the
manager's identity on the fund. This is the same defect class as the FDIC
recording Associated Banc-Corp's LEI on Associated Bank, N.A. (see the
bank-register-ontology build), now observed at a second US regulator.

### 4. GLEIF holds the reverse crosswalk the SEC does not

27,718 LEI records in the golden copy name EDGAR (RA000665) as their
registration authority: 22,688 carry an EDGAR series ID in registeredAs,
5,017 carry a CIK, 13 carry something else. GLEIF therefore publishes an
LEI-to-EDGAR-identifier mapping for 27,705 records, while no SEC surface
publishes a CIK-to-LEI or series-to-LEI file at all. The SEC's own series
and class register (19,340 series) has no LEI column.

### 5. The two halves of the series crosswalk disagree

Joining GLEIF's RA000665 series records against the series LEIs reported to
the SEC on N-PORT: 12,604 series are present on both sides; 12,504 agree;
100 disagree, meaning the same fund series carries two different LEIs on the
two sides of the register boundary. Specimen classes among the 100:

- Character-substitution twins: Voya Ultra Short Income ETF is
  `254900FKI2RDASVD0175` (valid, ISSUED) at GLEIF and
  `254900FK12RDASVD0175` on N-PORT; the reported variant substitutes "1" for
  "I" and fails the check digits. The checksum the SEC does not run would
  have caught its own data.
- Sibling swaps: three VictoryShares ETF series (S000093318, S000093319,
  S000093320) hold each other's LEIs cyclically between the two sides, the
  signature of a column-shift in a reporting pipeline.
- 50 series carry more than one LEI record at GLEIF.

Also: 6,149 GLEIF-registered series IDs are absent from the SEC's current
series and class register (the register covers current series; GLEIF records
persist for terminated ones; treat as coverage asymmetry, not error, until
per-series status is checked). 10,018 GLEIF-registered series had no N-PORT
LEI in 2026 Q2 (money market funds file N-MFP, not N-PORT; some funds file
semi-annually); 328 series reported an LEI on N-PORT with no GLEIF RA000665
record claiming them.

### 6. Status and resolution of the LEIs the SEC asserts

Joining every distinct valid LEI asserted on an SEC surface against the
golden copy classifies each as ISSUED, LAPSED, RETIRED-class, or absent
(dangling). Headline: 56.6 percent of ALL US LEI records are LAPSED
(202,698 of 358,294), materially worse than the global lapse rate; the
governance summary records the exact status distribution of SEC-asserted
LEIs. All 667 valid LEIs in the entity register itself resolve to golden-copy
records: the entity register's defects are emptiness and junk content, not
fabrication. Eleven checksum-valid LEIs asserted on the form surfaces
(N-PORT/N-CEN) do not exist in the golden copy at all
(reports/dangling_valid.json): plausible-looking identifiers that resolve to
nothing. A pipeline correction is recorded here honestly: an early build
mis-scoped the resolution join and briefly classified 557 entity-register
LEIs as dangling; the corrected join shows zero, and the governance gate now
covers this case.

### 7. Identifier quality at scale in the structured datasets

N-CEN 2026 Q2: 108,112 LEI cells across 20 tables; 92,558 valid; 57 fail
check digits; 6 all-zeros placeholders. N-PORT 2026 Q2: 5,347,869 holdings;
3,394,396 carry a valid issuer LEI; 19 fail check digits; 32 malformed.
Issuer CUSIPs: 3,543,498 valid, 20,728 fail the CUSIP check digit (0.58
percent of populated values). ISINs in the IDENTIFIERS table: 4,320,771
valid, 160 fail check digits. CUSIP values are analysed statistically and
never redistributed (licence).

### 8. The open ISIN-LEI mapping by country

9,135,428 mappings: DE 4,218,203 (46.2 percent), US 2,281,837 (25.0
percent), GB 650,214. 21,122 distinct LEIs carry US-prefixed ISINs.
CORRECTION recorded: an earlier scan-stage estimate of 12.4 percent US share
came from a partial, LEI-sorted sample and is superseded by this full-file
census. All 9,135,428 rows carry checksum-valid ISINs and LEIs; the file's
internal quality is clean; the finding is coverage, not conformance.

## What was NOT obtained or measured

- EDGAR full-text search for LEI strings in filing bodies: not attempted.
- N-MFP (money market funds) and 13F datasets: not fetched; the series
  coverage asymmetry in finding 5 cannot be fully decomposed without them.
- Historical quarters: one quarter (2026 Q2) of N-PORT/N-CEN only; trend
  claims are out of scope.
- MSRB/EMMA municipal identity: no open bulk access; skipped.
- OpenFIGI joins: deferred; the FIGI column of the scheme registry is
  declared but unexercised.
- Per-series status for the 6,149 GLEIF-only series IDs (requires the
  EDGAR series pages or historical series file; not fetched).
- The `rr` (relationships) and `repex` golden-copy files: not used.

## Reproduction

```
pipeline/download.sh                 # ~2.5 GB of register data
python3 pipeline/submissions_census.py
python3 pipeline/ncen_census.py
python3 pipeline/nport_census.py
python3 pipeline/isin_census.py
python3 pipeline/gleif_pass.py
python3 pipeline/reconcile_series.py
python3 pipeline/build_graph.py      # emits data/graph.ttl directly as text
python3 pipeline/governance_report.py  # dual-computation gate; non-zero on drift
```

Totals will drift as the registers move; the golden copy republishes daily
and EDGAR continuously.
