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
import tarfile
import tempfile
import zipfile
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


# Multi-file container formats, with their tarfile write mode (None => zip).
_CONTAINERS = {
    "zip": None,
    "tar": "w",
    "tgz": "w:gz",
    "tbz2": "w:bz2",
    "txz": "w:xz",
}


class ArchiveRepackConverter(Converter):
    """Repack a whole archive's contents into another container format.

    Supports zip ↔ tar ↔ tgz ↔ tbz2 ↔ txz by extracting every entry to a temp
    dir and rebuilding the archive — preserving the directory structure."""

    name = "stdlib archive repacker"
    category = "Archives"

    def outputs_for(self, src_ext: str) -> set[str]:
        ext = normalize_ext(src_ext)
        if ext in _CONTAINERS:
            return set(_CONTAINERS) - {ext}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)
        if src_ext not in _CONTAINERS or dst_ext not in _CONTAINERS:
            raise ConversionError(
                f"Archive repacking supports {sorted(_CONTAINERS)} only."
            )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._extract(src, src_ext, root)
                self._create(dst, dst_ext, root)
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Archive repacking failed: {exc}") from exc

    def _extract(self, src: Path, ext: str, dest: Path) -> None:
        if ext == "zip":
            with zipfile.ZipFile(src) as zf:
                zf.extractall(dest)
        else:
            with tarfile.open(src) as tf:
                tf.extractall(dest)

    def _create(self, dst: Path, ext: str, root: Path) -> None:
        files = sorted(p for p in root.rglob("*") if p.is_file())
        mode = _CONTAINERS[ext]
        if mode is None:  # zip
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, f.relative_to(root))
        else:
            with tarfile.open(dst, mode) as tf:
                for f in files:
                    tf.add(f, f.relative_to(root))
