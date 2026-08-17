# SERO outreach drafts (HUMAN-GATED: Fabio sends; nothing here is sent automatically)

Order: (1) Kendall call agenda (call already requested 17 Aug), (2) Manolova/GLEIF,
(3) Dean Ritz/Data Foundation. LinkedIn post last, after at least one reply.

## 1. Addition to the Kendall call agenda (no new email needed; use on the call)

Two US regulators, one defect class. The FDIC records Associated Banc-Corp's LEI
on Associated Bank, N.A.; the SEC's entity register records SunAmerica Asset
Management's LEI on SunAmerica Series Trust (CIK 892538), while the trust's own
N-PORT filings and GLEIF agree on the correct one. The xsd:pattern facet we
discussed for FIBO catches neither, because both values are syntactically valid.
This is the case for the companion data product covering register boundaries, and
it is why the FDIC introduction is valuable to both sides: the same audit runs on
BankFind and on EDGAR with the same open tooling.

## 2. Email: Zornitsa Manolova, GLEIF (follows the 16 Aug GODIN email)

Subject: 100 EDGAR series where GLEIF and SEC filings disagree on the LEI

Dear Ms Manolova,

Following my note to GODIN about the FDIC's downstream republication of LEIs, we
have completed the same audit for the SEC's registers, and part of the result is
directly useful to your data quality programme.

27,718 LEI records in the golden copy name EDGAR (RA000665) as their registration
authority. We reconciled the series identifiers in those records against the
series LEIs that the same funds report to the SEC on Form N-PORT. For 12,604
series the comparison is possible; 12,504 agree. One hundred do not, and the
disagreement classes are instructive: single-character substitutions where the
reported variant fails the ISO 7064 check digits, and three sibling ETFs holding
each other's LEIs in a cycle. Eleven checksum-valid LEIs reported to the SEC
resolve to no golden-copy record at all.

The full reconciliation, the ontology, and the pipeline are open at
github.com/fabio-rovai/securities-register-ontology, with a summary at
gov.tesseract.academy/research/securities-register-ontology. The machine-readable
disagreement list is in the repository. If it is useful to your team, or to the
challenge process on the registered side, I am glad to walk through the method.

Kind regards,
Fabio Rovai
Kampakis and Co Ltd, t/a The Tesseract Academy

## 3. Email: Dean Ritz, Data Foundation

Subject: An empirical baseline for FDTA implementation: the CIK-to-LEI gap, measured

Dear Dean,

Your paper on the FDTA as meaning sharing rather than file formats frames exactly
what we have been measuring. On 17 August we audited the boundary between the
SEC's entity register and the Global LEI System with an open OWL 2 and SHACL
ontology, the day's complete EDGAR bulk file, the GLEIF golden copy, and the 2026
Q2 N-PORT and N-CEN datasets.

The short version: the entity register's LEI field is populated for 773 of
981,355 entities; the SEC holds 1,973 registrant LEIs on its own forms and
surfaces 12 of them; GLEIF publishes an LEI-to-EDGAR crosswalk daily while no SEC
surface publishes the reverse; and 100 fund series carry different LEIs on the
two sides of the boundary. Every number is computed two independent ways and the
build fails if they disagree. The rule's own requirement for machine-readable
taxonomy or ontology models is what the artifact implements.

Everything is open: github.com/fabio-rovai/securities-register-ontology and
gov.tesseract.academy/research/securities-register-ontology. If a baseline like
this is useful to the Data Foundation's FDTA work, as a note, a webinar, or
simply as evidence for the implementation conversation, I would be glad to
contribute it. We have run the same audit on the FDIC's registers with parallel
findings.

Best regards,
Fabio Rovai
Kampakis and Co Ltd, t/a The Tesseract Academy

## 4. LinkedIn post (after a reply lands, not before)

There is no public CIK-to-LEI crosswalk. The SEC's entity register has an LEI
field on all 981,355 records and populates 773 of them. GLEIF publishes the
reverse mapping every day. On 1 October the LEI became the joint entity standard
for nine US agencies. We built the missing piece as an open ontology and audited
both sides of the boundary: 100 fund series carry two different LEIs depending on
which register you ask. Repo and method in the comments.

## Rules
- No em dashes anywhere. Full sentences. Numbers only from GOVERNANCE_SUMMARY.json.
- Re-run the pipeline before sending if more than a week has passed (totals drift).
- Do not send the challenge-facility route to GLEIF; Manolova/GODIN is the door
  (Fabio's standing ruling from the BRO strike).
