"""SVG (vector) conversions via svglib + reportlab.

Rasterises or re-renders an SVG into PNG/JPG/GIF/TIFF/BMP (bitmap) or PDF
(vector). Pure-Python and bundleable, so it works in the packaged app."""

from __future__ import annotations

from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

# reportlab's renderPM raster backend understands these.
_RASTER = {"png": "PNG", "jpg": "JPG", "jpeg": "JPG", "gif": "GIF", "tiff": "TIFF",
           "tif": "TIFF", "bmp": "BMP"}


class SvgConverter(Converter):
    name = "SVG vector converter"
    category = "Images"

    def __init__(self) -> None:
        import importlib.util

        self._ok = (
            importlib.util.find_spec("svglib") is not None
            and importlib.util.find_spec("reportlab") is not None
        )

    def available(self) -> bool:
        return self._ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if self._ok and normalize_ext(src_ext) == "svg":
            return set(_RASTER) | {"pdf"}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        from svglib.svglib import svg2rlg

        dst_ext = normalize_ext(dst.suffix)
        try:
            drawing = svg2rlg(str(src))
            if drawing is None:
                raise ConversionError("Could not parse the SVG file.")

            if dst_ext == "pdf":
                from reportlab.graphics import renderPDF

                renderPDF.drawToFile(drawing, str(dst))
            elif dst_ext in _RASTER:
                from reportlab.graphics import renderPM

                renderPM.drawToFile(drawing, str(dst), fmt=_RASTER[dst_ext])
            else:
                raise ConversionError(f"Cannot convert SVG to .{dst_ext}")
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"SVG conversion failed: {exc}") from exc
