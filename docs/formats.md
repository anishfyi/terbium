# Formats

terbium ships adapters for PDF, PPTX, XLSX, CSV, and image files (PNG/JPG/JPEG/
WEBP/TIFF). Each turns bytes on disk into the same normalized shape: positioned
`Word`s, `ImageRef`s, and (where the format exposes one) a native table.
Everything smart happens after, on that uniform view.

For the reverse question, which kinds of documents exist and which lane reads
each, see [TAXONOMY.md](TAXONOMY.md).

## PDF

The hard case, and where the geometry engine runs in full.

1. **Word geometry.** PyMuPDF gives spans with boxes and font sizes; terbium
   splits them into positioned tokens.
2. **De-heading.** Text that repeats near the same edge across many pages is a
   running header or footer, and is stripped. Mid-page repeats (like an axis
   label) are deliberately kept.
3. **Spread splitting.** A landscape page with an empty central gutter is a
   two-page spread; terbium cuts it so the left product does not merge with the
   right.
4. **Table reconstruction (content-agnostic).** A run of consecutive lines that
   share the same column structure is a table. Column anchors come from the
   x-positions of the cells, the first row becomes the header, and every cell is
   placed by x-alignment. It makes no assumption about what the cells contain, so
   a financial table, a spec sheet, and a furniture matrix all reconstruct the
   same way. Multi-column prose is rejected (its cells are sentence fragments, not
   data). The furniture size x finish cross-tab is a special case the `furniture`
   schema interprets on top of the generic grid.

### Beyond matrices

Not every PDF is a dimension x finish matrix.

- **Label grids.** A lookbook is a grid of product photos with a name under each.
  terbium uses a per-page lookbook heuristic (not whole-document all-or-nothing):
  it segments each row into separate labels, stitches wrapped names back together,
  and groups them under the page's collection title. Sparse pages (1-2 photos) and
  dense grids (8-12+ products/page) are both supported.
- **Image-only pages.** A page with images but no text layer cannot be read
  algorithmically. terbium records these and reports them, so an image catalogue
  returns an honest "these pages need the vision lane" instead of nothing.

## PPTX

python-pptx exposes shapes with positions, native tables (rows and cells, no
reconstruction), and pictures with real pixels. terbium hands tables straight
through as high-confidence records and only falls back to geometry for
free-floating text boxes.

## XLSX

openpyxl reads cells and merged ranges. Merged header cells are propagated across
their span so multi-column headers survive. One sheet becomes one page.

## CSV

The delimiter, encoding, and whether a header row exists are all sniffed. Values
become a single native table. The easy case, handled honestly.

## Images (PNG/JPG/JPEG/WEBP/TIFF)

Standalone image files become a single `Page` with one `ImageRef`. Words are
synthesized via the local Tesseract bridge when installed. See [documents.md](documents.md).

## Adding a format

Subclass `terbium.documents.base.DocumentAdapter`, set `extensions`, implement
`parse(path) -> list[Page]`, and decorate the class with `@register`. If your
format has native tables, attach them to `Page.native_tables` and terbium will
skip geometry reconstruction for that page.
