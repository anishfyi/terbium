"""Self-contained HTML from records with a never-crash fallback chain.

rich styled HTML -> minimal valid HTML -> plain pre CSV
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Sequence

from .csv_out import records_to_csv


def _rows_from_records(records) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for r in records:
        if hasattr(r, "fields"):
            row = {"sku": getattr(r, "sku", "") or "",
                   "confidence": getattr(r, "confidence", 0)}
            row.update(r.fields)
            rows.append(row)
        else:
            rows.append(dict(r))
    return rows


def _collect_columns(rows: Sequence[Dict[str, Any]]) -> List[str]:
    keys: List[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    return keys


def _rich_html(rows: List[Dict[str, Any]]) -> str:
    cols = _collect_columns(rows)
    head_cells = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in cols)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>terbium output</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
body {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       margin: 2rem; color: #1a1a1a; background: #fafafa; }}
h1 {{ font-size: 1.25rem; font-weight: 600; }}
table {{ border-collapse: collapse; width: 100%; background: #fff;
         box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
th, td {{ border: 1px solid #e0e0e0; padding: 0.5rem 0.75rem; text-align: left;
          font-size: 0.875rem; }}
th {{ background: #f0f0f0; font-weight: 600; }}
tr:nth-child(even) td {{ background: #f9f9f9; }}
</style>
</head>
<body>
<h1>terbium output</h1>
<table>
<thead><tr>{head_cells}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</body>
</html>"""


def _minimal_html(rows: List[Dict[str, Any]]) -> str:
    cols = _collect_columns(rows)
    lines = ["<html><body><table border='1'>"]
    lines.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in cols) + "</tr>")
    for row in rows:
        lines.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in cols) + "</tr>")
    lines.append("</table></body></html>")
    return "\n".join(lines)


def render_html(records) -> str:
    """Render records as self-contained HTML; never raises."""
    try:
        rows = _rows_from_records(records)
        if not rows:
            return "<!DOCTYPE html><html><body><p>No records.</p></body></html>"
        for renderer in (_rich_html, _minimal_html):
            try:
                return renderer(rows)
            except Exception:
                continue
        return f"<pre>{html.escape(records_to_csv(rows))}</pre>"
    except Exception:
        return "<html><body><pre>output unavailable</pre></body></html>"
