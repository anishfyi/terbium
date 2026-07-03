# Formats

terbium ships four first-class adapters. Each turns bytes on disk into the same
normalized shape: positioned `Word`s, `ImageRef`s, and (where the format exposes
one) a native table. Everything smart happens after, on that uniform view.

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
4. **Grid reconstruction.** Column anchors come from the x-positions of the cells;
   row headers are the dimension-led lines; the finish names above become column
   headers. Every article number is placed into its cell by x-alignment.

### Beyond matrices

Not every PDF is a dimension x finish matrix.

- **Label grids.** A lookbook is a grid of product photos with a name under each.
  When a document is mostly not matrices, terbium enters lookbook mode: it
  segments each row into separate labels, stitches wrapped names back together,
  and groups them under the page's collection title. One record per product.
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

## Adding a format

Subclass `terbium.documents.base.DocumentAdapter`, set `extensions`, implement
`parse(path) -> list[Page]`, and decorate the class with `@register`. If your
format has native tables, attach them to `Page.native_tables` and terbium will
skip geometry reconstruction for that page.
