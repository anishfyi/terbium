"""Importing this package registers every adapter as a side effect."""
from .base import DocumentAdapter, get_adapter, register, supported_extensions
from . import pdf as _pdf
from . import pptx_adapter as _pptx
from . import xlsx_adapter as _xlsx
from . import csv_adapter as _csv
from . import image_adapter as _image

__all__ = ["DocumentAdapter", "get_adapter", "register", "supported_extensions"]
