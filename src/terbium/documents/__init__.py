"""Importing this package registers every adapter as a side effect."""
from .base import DocumentAdapter, get_adapter, register, supported_extensions
from . import pdf as _pdf
from . import pptx_adapter as _pptx
from . import xlsx_adapter as _xlsx
from . import csv_adapter as _csv

__all__ = ["DocumentAdapter", "get_adapter", "register", "supported_extensions"]
