# Forty-five days before the LEI becomes the US entity standard, the SEC's register of 981,355 entities lists 773

On 1 October 2026, the joint data standards rule under the Financial Data
Transparency Act takes effect. Nine federal financial agencies, the SEC among
them, adopted the ISO 17442 Legal Entity Identifier as their common legal
entity identifier, and the rule's operative text requires data schemas with
semantics documented in machine-readable taxonomy or ontology models. We took
that requirement literally. On 17 August 2026 we downloaded the SEC's entire
entity register and every open register that embeds or is embedded by it, and
we measured what the public record actually says.

This is a case study in register assurance: the practice of auditing what a
register publishes against the rules its identifiers declare for themselves
and against the other registers that carry the same identity. Everything
below is reproducible from the open repository, every headline is computed
two independent ways, and the pipeline fails its own build if the two ever
disagree.

## What we measured

Four register surfaces, all keyless, all fetched on the same day.

The EDGAR bulk submissions file is the SEC's entity register: 981,355 entity
records, refreshed daily, one JSON document per CIK. Every record carries a
top-level field named `lei`.

The GLEIF golden copy is the global LEI register: 3,403,856 records in the
17 August publish, of which 358,275 are US entities.

The SEC's structured form datasets for 2026 Q2 record what regulated funds
told the SEC on Forms N-PORT and N-CEN, including their own LEIs, their
series' LEIs, and the LEIs and CUSIPs of 5.3 million portfolio holdings.

The GLEIF ISIN-LEI mapping file links 9,135,428 securities to their issuers'
LEIs, openly and daily.

## Finding one: the field is empty

The `lei` field is populated in 773 of 981,355 EDGAR entity records. That is
0.079 percent. Among the 7,992 listed operating companies in the register,
25 carry an LEI. Apple's LEI has been ISSUED at GLEIF since 2012; its EDGAR
record says null. The same is true of essentially every household-name
filer.

The operational consequence is direct. Any institution that needs to join
SEC filings to sanctions lists, to counterparty risk systems, to Basel
reporting, or to any of the datasets keyed on the LEI cannot do it from the
SEC's register. Every consumer of EDGAR data rebuilds the same crosswalk
privately, badly, or not at all. From 1 October the identifier the register
ignores is the standard the register's operator has adopted.

## Finding two: what the field contains when it is not empty

Of the 773 populated values, 667 are valid LEIs. The other 106 are a museum
of what happens when a register publishes a field it never validates. There
are telephone numbers, including "(646) 508-0022" and "424-231-9100". There
are IRS employer identification numbers. There are entity names typed into
the identifier field, including "DANGEROUS 7 SPV 2 LP" and
"WUWALLACEFAMILYTRUST". There is a Connecticut state registry string,
"US-CT.BER:3091043". There are fourteen 20-character strings that look like
LEIs and fail the ISO 7064 check digits, and there are thirty-five records
whose LEI is the literal text "N/A".

The LEI carries two check digits precisely so that software can reject a
corrupted value. The same government already relies on this: a HMDA loan
identifier must begin with a valid LEI and end with a computable check
digit, by regulation. EDGAR runs no such check on its own LEI field and
republishes whatever was filed.

## Finding three: the SEC holds the crosswalk it does not publish

In a single quarter, 1,973 fund registrants stated their LEI to the SEC on
Forms N-PORT and N-CEN. The entity register surfaces 12 of them. For 1,954
CIKs we can show the operator holds a valid LEI on one publication surface
while the entity register's field for the same CIK sits empty. Silence here
is not missing data; it is a published position of the register, and it is
wrong.

Where both surfaces are populated they can disagree. The entity register
says CIK 892538, SunAmerica Series Trust, has LEI 549300E40BQMHI2LOX26.
GLEIF says that LEI belongs to SunAmerica Asset Management, LLC, the trust's
investment adviser. The trust's own filings on Form N-PORT report
549300YDIAXUNCUXFM44, which GLEIF registers as SunAmerica Series Trust
against exactly this CIK. The register carries the manager's identity on the
fund. We found the same defect class last week in a different US register:
the FDIC's BankFind record for Associated Bank, N.A. carries the LEI of its
holding company. Two regulators, one failure mode: identity assigned to the
wrong side of a control relationship at the register boundary.

## Finding four: the reverse crosswalk exists, at GLEIF

27,704 LEI records in the golden copy name EDGAR as their registration
authority and carry an EDGAR identifier in their registeredAs field: 22,672
series IDs and 5,019 CIKs. GLEIF, a Swiss foundation, publishes a mapping
from LEIs to SEC identifiers every day under CC0. The SEC publishes no
mapping in either direction, and its own investment company series and class
register, 19,340 series, has no LEI column at all. The authoritative
crosswalk between the US securities register and the US-adopted entity
standard is maintained outside the United States, by the counterparty
register.

## Finding five: the two halves disagree 100 times

Because GLEIF records which EDGAR series each LEI belongs to, and because
funds report their series LEIs to the SEC on N-PORT, the two halves of the
same mapping can be reconciled for 12,604 series. They agree 12,504 times.
One hundred fund series carry two different LEIs on the two sides of the
register boundary.

The specimens tell you how identity actually decays. Voya Ultra Short
Income ETF is 254900FKI2RDASVD0175 at GLEIF, ISSUED and valid. Its N-PORT
filings say 254900FK12RDASVD0175, with the letter I replaced by the digit 1.
The reported variant fails the check digits, so the checksum the SEC does
not run would have caught the SEC's own data. Three VictoryShares ETF
series hold each other's LEIs in a cycle, the unmistakable signature of a
column shift in someone's reporting pipeline, now frozen into regulatory
filings. Eleven checksum-valid LEIs reported to the SEC do not exist in the
GLEIF golden copy at all: plausible identifiers that resolve to nothing.

The operational consequence: any system that keys fund exposure, fee
analysis, or counterparty aggregation on the reported LEI will silently
split one fund into two entities or merge two into one, and no schema
validator on either register can see it, because each register is
internally consistent. The defect exists only at the boundary.

## Finding six: most US LEIs are not current anyway

Of 358,275 US LEI records, 202,698 are LAPSED: 56.6 percent, materially
worse than the global lapse rate. Among the LEIs asserted on SEC surfaces
the status distribution is better but not clean, and the full breakdown is
in the repository's governance summary. Adoption without renewal is not
identification; it is an inventory of expired claims.

## The method, transferable

None of this required privileged access. The method is the same one we have
now run against fund registers, insurance registers, scholarly records, bank
registers, learning standards, and enterprise knowledge bases.

First, model identity honestly. An identifier in a register is not a
property of an entity; it is a dated claim by a named register. Our OWL
model reifies every published value as an IdentifierAssertion carrying the
value exactly as published, the scheme the field claims, whether the value
conforms to the rules that scheme declares for itself, and, for LEIs,
whether the value resolves at GLEIF and with what status.

Second, make the schemes self-describing. A SKOS registry declares each
scheme's length, character set, and check-digit algorithm as data, so the
validator has no hard-coded rules and adding a register means adding data,
not code.

Third, make defects first-class. Each defect class is one SHACL shape, so
the validation report is the findings table. Cross-register comparisons are
ReconciliationObservation nodes; a register holding an identifier on one
surface while another sits empty is a CoverageObservation.

Fourth, never trust one computation. Every headline is computed set-based in
Python and independently via SPARQL and SHACL over the graph, and the build
fails if they disagree. This gate has caught a real bug in every register we
have audited, including, twice, our own pipelines.

## Prior art, credited

FIBO, maintained by the EDM Association, models legal entities and US
registry identifiers conceptually, and its maintainers are actively
improving LEI constraints; our findings sit downstream of FIBO's scope, at
the layer where published values meet declared rules. The OFR's 2018 staff
discussion paper by Liju Fan and Mark Flood prototyped OWL over bank
registry data and remains the closest federal prior art. The Data
Foundation's work on FDTA implementation, including its argument that the
Act is about meaning sharing rather than file formats, frames the policy
need this measurement serves. GLEIF's own data quality programme assures
what issuers submit; nothing in it constrains what a downstream register
republishes, which is exactly the gap measured here.

## What a regulator or a fund complex should do with this

If you operate a register: validate identifier fields against their schemes
at ingestion, publish the crosswalks you already hold, and treat an empty
field as an assertion you are making. If you run regulatory reporting at a
fund complex: reconcile your reported LEIs against the golden copy
quarterly; the 100 disagreements above are all detectable from your side
with the checksums and the open files.

If you want this run against a register you operate or depend on, we run a
scoped diagnostic of one register boundary as a one-week engagement:
harvest, conformance census, cross-register reconciliation, and a findings
ledger your engineers can reproduce. Write to fabio@thetesseractacademy.com
with the register name.

The repository, with the ontology, the SHACL layers, the pipeline, and the
build report, is public:
github.com/fabio-rovai/securities-register-ontology.
