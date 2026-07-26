# The document taxonomy

A deep list of the PDF and PPTX documents that exist in the wild, grouped by
**layout archetype**, because the archetype, not the filename or the business
domain, decides which terbium lane can read it. Two documents with the same
name (an "invoice" from SAP and an "invoice" from a freelancer's Canva template)
can be different archetypes; two documents from different domains (a furniture
lookbook and a real estate brochure) are the same one.

Each entry lists: typical fields worth extracting, the layout tells a
classifier can key on, and the lane that handles it. Priority marks what this
release targets versus what is honestly queued.

## Archetype A: image-anchored grids (catalog lane)

One entity per photo, text clustered near each image. The image is the anchor;
the words around it are the record.

| Document | Typical fields | Layout tells |
|---|---|---|
| Product catalog | sku, name, price, materials, dimensions, photo | repeating photo+caption units, SKU-like tokens |
| Lookbook / collection book | name, collection, photo | minimal text, large photos, one name per photo |
| Line sheet (wholesale) | sku, name, wholesale price, MOQ, photo | denser grid, smaller photos, price column |
| Real estate brochure | address, price, beds/baths, sqft, photo | hero photo + spec block, one property per page or spread |
| Restaurant menu (photo) | dish, description, price, photo | photo + name + dotted price leaders |
| Fashion/apparel catalog | style no, colorways, sizes, photo | swatch rows under photos, size runs |
| Jewelry/accessories catalog | sku, name, stones/metals, price, photo | small photos, dense spec captions |
| Art/portfolio book | title, artist, medium, year, photo | one image per page, museum-style caption |
| Parts catalog (industrial) | part no, name, spec, diagram | exploded diagrams, dense part numbers |
| Seed/plant catalog | variety, latin name, days, price, photo | grid of small photos + coded attributes |

**Lane:** `build_catalog` + `layout/labels.py` + `extract.py`. Priority: this
release hardens the picture-heavy end (dense grids, sparse-photo pages, mixed
decks). See `docs/catalog.md`.

## Archetype B: forms and key-value documents (transaction lane)

Short documents built from labeled fields, usually with one tabular region.
The label is the anchor; the value sits right of it, under it, or in a box.

| Document | Typical fields | Layout tells |
|---|---|---|
| Invoice | number, date, due date, vendor, bill-to, line items, subtotal, tax, total | "invoice", "bill to", amount column, totals block at bottom right |
| Bill / utility bill | account no, period, usage, due date, amount due | "amount due", "service period", meter/usage table |
| Receipt (paper/POS) | merchant, datetime, items, total, payment, change | narrow column, item-left/price-right pairs, "total", "cash/card" |
| Receipt (e-mail/thermal scan) | same as above | same, often image-only |
| Purchase order | PO no, vendor, ship-to, line items, terms | "purchase order", "ship to", qty/unit price columns |
| Quote / estimate | quote no, valid-until, line items, total | "quote"/"estimate", expiry date, optional checkbox items |
| Credit / debit note | note no, ref invoice, lines, total | "credit note", references an invoice number |
| Packing slip / delivery note | order no, ship-to, items, qty | no prices, qty-only table, "ship to" |
| Proforma invoice | same as invoice | "proforma" |
| Tax form (W-2, 1099, GST/VAT return) | boxes with numbers, ids, amounts | numbered boxes, government header, fixed layout |
| Bank statement | account, period, transaction lines, balances | date/description/amount running table, opening/closing balance |
| Credit card statement | same + card meta | same, "minimum payment due" |
| Payslip | employee, period, earnings/deductions, net pay | two-column earnings/deductions grid, "net pay" |
| Insurance EOB / claim | claim no, patient, service lines, allowed/paid/owed | dense codes, multi-amount columns |
| Shipping label | addresses, tracking no, service, weight | huge barcode/QR, bold address block, few fields |
| Ticket / boarding pass | passenger, from/to, date, seat, gate, code | single event, big codes, QR, time-heavy |
| Certificate (completion, birth, incorporation) | names, dates, issuer, registration no | centered layout, seals/signatures, little structure |
| Customs/commercial invoice | invoice fields + HS codes, origin, weights | HS code column, country fields |
| Expense report | employee, dates, category/amount lines, total | receipt-like lines grouped by date/category |

**Lane:** `layout/forms.py` (key-value geometry) + the content-agnostic table
detector for line items + `schema/transaction.py`. Receipts and labels lean on
the OCR lane (image adapter + Tesseract). Priority: invoices, bills, receipts,
POs, quotes this release; statements and payslips are the same machinery with
different synonyms; tax forms and EOBs later (fixed-template territory).

## Archetype C: sectioned prose (resume lane)

Long documents organized by headings. The heading, in a bigger or bolder font,
is the anchor; the block under it is the record.

| Document | Typical fields | Layout tells |
|---|---|---|
| Resume / CV | name, contacts, links, summary, experience entries, education, skills | section headers (EXPERIENCE, EDUCATION), date ranges, job-title lines |
| Academic CV | + publications, grants, talks | very long, citation lists |
| Cover letter | sender, recipient, date, body | letter salutation, single flow |
| Contract / agreement | parties, effective date, clauses, signatures | numbered clauses, "whereas", signature block |
| Business report | title, exec summary, sections, tables | TOC, numbered headings, embedded charts |
| Whitepaper | same, more marketing | same, callout boxes |
| Academic paper | title, authors, abstract, sections, references | two columns, "abstract", numbered refs |
| Manual / user guide | product, sections, steps, warnings | numbered steps, warning boxes, TOC |
| Spec sheet / datasheet | product, feature table, ratings | one or two pages, dense spec table |
| Proposal / SOW | parties, scope sections, pricing table | narrative + a pricing table |
| Meeting minutes | date, attendees, agenda items, actions | bullet-heavy, names + action verbs |

**Lane:** section detection from font size/weight + date-range and contact
regexes + `schema/resume.py`. Priority: resumes/CVs this release (HR tech is a
target market); contracts and papers are prose, so the honest output is
section records, not fake tabulation; later.

## Archetype D: native or geometric grids (already handled)

The table is the document.

| Document | Typical fields | Layout tells |
|---|---|---|
| Price list | sku, name, price columns | long uniform table, price columns |
| Financial statement | line items x periods | period headers, indented rows, totals |
| Inventory/stock list | sku, name, qty, location | qty column, location codes |
| Schedule / timetable | times x days/resources | time tokens in headers or first column |
| Rate card | service, tier, rate | short table, currency column |
| Comparison chart | features x products | checkmark/yes-no cells |
| Bill of materials | part no, qty, unit, description | nested part numbers |
| Grade sheet / marksheet | student, subject scores | name rows, score columns |
| Attendance/payroll register | name x date grid | date headers, mark cells |
| Election/sports results table | name, votes/points, rank | rank column, numeric body |
| Menu (text only) | item, price | dot leaders to prices |
| Directory / contact list | name, phone, email columns | repeating contact patterns |

**Lane:** `layout/tables.detect_tables` (content-agnostic) plus native tables
from the PPTX/XLSX/CSV adapters, `schema/product` or `schema/generic`.
Priority: done; regressions guarded by tests.

## Archetype E: slide decks (PPTX lane)

| Document | Typical fields | Layout tells |
|---|---|---|
| Pitch deck | problem/solution/market slides | big titles, little body text |
| Product deck (catalog deck) | one product per slide, photo + specs | repeating slide layout, photos |
| Financial review deck | KPI slides, table slides | native tables, chart images |
| Lecture/training deck | titled bullet slides | bullets, slide numbers |
| Photo deck / portfolio | full-bleed images, captions | image-only slides |

**Lane:** PPTX adapter native tables + picture extraction; product decks go
through the catalog lane. Priority: product decks this release via the
per-page label lane; the rest are honestly prose with occasional tables.

## Archetype F: flowing prose (out of scope for rows)

Books, novels, newsletters, essays, magazines, brochures of pure narrative.
There is no record structure to reconstruct; terbium will classify these as
`unknown` and say so rather than invent rows. If a future lane serves them, it
is a chapters/sections outline, and it is not this release.

## Classification signals summary

Cheap signals computed per page, combined in `terbium.classify`:

- **Photo density and count.** Many photos with short nearby text: archetype A.
- **Keyword hits.** "invoice", "bill to", "amount due", "total", "resume",
  "experience", "education", "abstract", "purchase order": archetypes B and C.
- **Colon-terminated short lines.** Many of them: archetype B key-value.
- **Currency/date density.** High near the right edge: archetype B totals;
  date ranges at line starts: resume experience.
- **Column regularity.** Repeating x-aligned multi-cell rows: archetype D.
- **Section headers.** Bold/size outliers spaced down the page: archetype C.
- **None of the above, mostly prose:** archetype F, reported honestly.

The classifier suggests; `--type` overrides. A wrong guess costs a re-run with
a flag, never silent garbage.
