"""Universal render package: CSV, terminal table, HTML."""
from .csv_out import records_to_csv, to_csv
from .html import render_html
from .terminal import render_terminal_table

__all__ = ["to_csv", "records_to_csv", "render_terminal_table", "render_html"]
