from .base import Schema, get_schema, register_schema
from . import generic as _generic
from . import furniture as _furniture
from . import product as _product
from . import transaction as _transaction
from . import resume as _resume

__all__ = ["Schema", "get_schema", "register_schema"]
