"""The Everything Converter — convert (almost) any file into (almost) any other.

Public API:
    >>> from everythingconverter import Registry
    >>> reg = Registry()
    >>> reg.convert("cat.jpg", "cat.png")
"""

from .converters import ConversionError, normalize_ext
from .registry import Registry, Target, default_registry

__version__ = "0.1.0"
__all__ = [
    "Registry",
    "Target",
    "default_registry",
    "ConversionError",
    "normalize_ext",
    "__version__",
]
