"""Base classes and helpers shared by all converters.

A *converter* knows how to turn a file of one extension into a file of
another extension. Each converter advertises which output extensions it can
produce for a given input extension via :meth:`Converter.outputs_for`, and
reports whether its underlying backend (ffmpeg, pandoc, a Python lib, ...) is
actually installed via :meth:`Converter.available`.

The registry stitches all converters together into a single "convert anything
to anything" graph.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class ConversionError(RuntimeError):
    """Raised when a conversion fails for a reason we can explain to the user."""


def normalize_ext(name_or_ext: str) -> str:
    """Return a lowercase extension without a leading dot.

    Accepts a bare extension (``"PNG"``, ``".png"``) or a full path/filename
    (``"/tmp/cat.PNG"``) and always returns ``"png"``.
    """
    text = str(name_or_ext).strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.lstrip(".")


class Converter(ABC):
    """Abstract base for every conversion backend."""

    #: Human readable name shown in the UI / logs.
    name: str = "converter"
    #: Broad category used purely for display ("Images", "Audio", ...).
    category: str = "Other"

    @abstractmethod
    def outputs_for(self, src_ext: str) -> set[str]:
        """Return the set of output extensions reachable from ``src_ext``."""

    @abstractmethod
    def convert(self, src: Path, dst: Path, **options) -> None:
        """Convert ``src`` into ``dst``. Raise :class:`ConversionError` on failure."""

    def available(self) -> bool:
        """Whether this converter's backend is usable on this machine."""
        return True

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        return normalize_ext(dst_ext) in self.outputs_for(normalize_ext(src_ext))


def require_tool(tool: str, hint: str = "") -> str:
    """Return the absolute path to a CLI tool or raise a friendly error."""
    path = shutil.which(tool)
    if not path:
        extra = f" {hint}" if hint else ""
        raise ConversionError(f"Required tool '{tool}' was not found on PATH.{extra}")
    return path
