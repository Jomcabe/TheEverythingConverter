"""The conversion registry: the brain that turns *anything* into *anything*.

It collects every :class:`Converter`, then answers two questions the UI and CLI
care about:

1. Given a source extension, what target formats are possible? (:func:`targets_for`)
2. Given a source + target extension, which converter should run? (:func:`find_converter`)

Converters whose backend is missing are still listed (so we can tell the user
*why* something is unavailable) but are skipped when actually picking one to run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .converters import (
    ArchiveRepackConverter,
    AudioConverter,
    CompressionConverter,
    ConfigConverter,
    Converter,
    ConversionError,
    DataConverter,
    DocxConverter,
    ImageConverter,
    LibreOfficeConverter,
    MarkupConverter,
    PandocConverter,
    PdfConverter,
    SubtitleConverter,
    SvgConverter,
    VideoConverter,
    normalize_ext,
)


def _build_converters() -> list[Converter]:
    """Instantiate all converters in priority order (first available wins).

    Ordering notes:
    * SVG is handled by its own converter before generic media.
    * Pure-Python markup (md/html/txt) ranks above pandoc/LibreOffice because it
      renders Markdown properly and always works (bundled in the app).
    * LibreOffice ranks above the pure-Python DOCX converter so it wins for
      complex Office files when installed; DocxConverter is the universal
      fallback when it isn't.
    """
    return [
        ImageConverter(),
        SvgConverter(),
        AudioConverter(),
        VideoConverter(),
        SubtitleConverter(),
        MarkupConverter(),   # before DataConverter so HTML *documents* go here,
        DataConverter(),     # while HTML *tables* -> csv/xlsx still fall to pandas
        ConfigConverter(),
        PdfConverter(),
        PandocConverter(),
        LibreOfficeConverter(),
        DocxConverter(),
        CompressionConverter(),
        ArchiveRepackConverter(),
    ]


@dataclass(frozen=True)
class Target:
    """A reachable output format and the converter/category behind it."""

    ext: str
    category: str
    converter: str
    available: bool


class Registry:
    def __init__(self, converters: list[Converter] | None = None) -> None:
        self.converters = converters if converters is not None else _build_converters()

    # -- discovery ---------------------------------------------------------
    def targets_for(self, src: str) -> list[Target]:
        """Return all reachable targets for a source extension/filename.

        Deduplicated by extension, preferring an *available* converter when more
        than one can produce the same output.
        """
        src_ext = normalize_ext(src)
        best: dict[str, Target] = {}
        for conv in self.converters:
            avail = conv.available()
            for out in conv.outputs_for(src_ext):
                out = normalize_ext(out)
                if out == src_ext:
                    continue  # no-op conversion
                existing = best.get(out)
                if existing is None or (avail and not existing.available):
                    best[out] = Target(out, conv.category, conv.name, avail)
        return sorted(best.values(), key=lambda t: (t.category, t.ext))

    def available_targets(self, src: str) -> list[str]:
        return [t.ext for t in self.targets_for(src) if t.available]

    def find_converter(self, src: str, dst: str) -> Converter | None:
        """Return the first *available* converter for this pair, if any."""
        src_ext, dst_ext = normalize_ext(src), normalize_ext(dst)
        fallback: Converter | None = None
        for conv in self.converters:
            if dst_ext in {normalize_ext(o) for o in conv.outputs_for(src_ext)}:
                if conv.available():
                    return conv
                fallback = fallback or conv
        return fallback  # unavailable, but at least explains the missing backend

    # -- execution ---------------------------------------------------------
    def convert(self, src: Path, dst: Path, **options) -> Path:
        src, dst = Path(src), Path(dst)
        if not src.exists():
            raise ConversionError(f"Source file not found: {src}")
        conv = self.find_converter(src.suffix, dst.suffix)
        if conv is None:
            raise ConversionError(
                f"No converter knows how to turn .{normalize_ext(src.suffix)} "
                f"into .{normalize_ext(dst.suffix)}."
            )
        if not conv.available():
            # Run anyway so the converter raises its specific install hint.
            pass
        dst.parent.mkdir(parents=True, exist_ok=True)
        conv.convert(src, dst, **options)
        return dst

    # -- diagnostics -------------------------------------------------------
    def backend_status(self) -> list[tuple[str, str, bool]]:
        """(name, category, available) for every converter."""
        return [(c.name, c.category, c.available()) for c in self.converters]


# A shared default instance for convenience.
default_registry = Registry()
