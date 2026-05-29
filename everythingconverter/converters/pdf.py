"""PDF conversions powered by PyMuPDF (``pip install pymupdf``).

Covers the directions the other backends miss:
* PDF -> images (png/jpg/tiff/...), one file per page (or a single page).
* PDF -> plain text / html.
* images -> PDF and text/markdown/html -> PDF are handled by the image and
  document converters respectively.
"""

from __future__ import annotations

from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

_IMAGE_OUT = {"png", "jpg", "jpeg", "tiff", "tif", "ppm", "pgm"}
_TEXT_OUT = {"txt", "html"}


class PdfConverter(Converter):
    name = "PyMuPDF PDF converter"
    category = "Documents"

    def __init__(self) -> None:
        try:
            import fitz  # noqa: F401  (PyMuPDF)

            self._ok = True
        except ImportError:
            self._ok = False

    def available(self) -> bool:
        return self._ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self._ok:
            return set()
        if normalize_ext(src_ext) == "pdf":
            return set(_IMAGE_OUT) | set(_TEXT_OUT)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        import fitz

        dst_ext = normalize_ext(dst.suffix)
        try:
            doc = fitz.open(src)
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Could not open PDF: {exc}") from exc

        try:
            if dst_ext in _TEXT_OUT:
                self._to_text(doc, dst, dst_ext)
            elif dst_ext in _IMAGE_OUT:
                self._to_images(doc, dst, dst_ext, **options)
            else:
                raise ConversionError(f"Cannot convert PDF to .{dst_ext}")
        finally:
            doc.close()

    def _to_text(self, doc, dst: Path, ext: str) -> None:
        mode = "html" if ext == "html" else "text"
        parts = [page.get_text(mode) for page in doc]
        if ext == "html":
            body = "\n".join(parts)
            dst.write_text(f"<!doctype html><meta charset='utf-8'>\n{body}")
        else:
            dst.write_text("\n\f\n".join(parts))

    def _to_images(self, doc, dst: Path, ext: str, **options) -> None:
        import fitz

        dpi = int(options.get("dpi", 150))
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        page_index = options.get("page")  # 1-based, optional

        if page_index is not None:
            pages = [int(page_index) - 1]
        else:
            pages = list(range(doc.page_count))

        normalized = "jpg" if ext == "jpeg" else ext
        multi = len(pages) > 1
        for n in pages:
            pix = doc[n].get_pixmap(matrix=matrix)
            if multi:
                out = dst.with_name(f"{dst.stem}_p{n + 1}.{normalized}")
            else:
                out = dst
            pix.save(str(out))
