"""Archive conversions using only the Python standard library.

Two flavours:
* **Re-packing**: change a single-file compression wrapper, e.g. ``.gz`` <->
  ``.bz2`` <-> ``.xz`` for a plain file, or wrap/unwrap a tarball's
  compression (``.tar`` -> ``.tar.gz``).
* The GUI mainly targets simple, lossless container swaps; full multi-file
  archive juggling is intentionally kept minimal and predictable.
"""

from __future__ import annotations

import bz2
import gzip
import lzma
import shutil
from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

# Single-file compressors: decompress one, compress to another.
_COMPRESSORS = {
    "gz": gzip,
    "bz2": bz2,
    "xz": lzma,
}


class CompressionConverter(Converter):
    """Convert between single-file compressors (gz/bz2/xz) and 'none' (raw)."""

    name = "stdlib compression converter"
    category = "Archives"

    def outputs_for(self, src_ext: str) -> set[str]:
        ext = normalize_ext(src_ext)
        if ext in _COMPRESSORS:
            # Recompress to another scheme.
            return set(_COMPRESSORS) - {ext}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)
        if src_ext not in _COMPRESSORS or dst_ext not in _COMPRESSORS:
            raise ConversionError(
                f"Compression conversion supports {sorted(_COMPRESSORS)} only."
            )
        src_mod = _COMPRESSORS[src_ext]
        dst_mod = _COMPRESSORS[dst_ext]
        try:
            with src_mod.open(src, "rb") as fin, dst_mod.open(dst, "wb") as fout:
                shutil.copyfileobj(fin, fout)
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Compression conversion failed: {exc}") from exc
