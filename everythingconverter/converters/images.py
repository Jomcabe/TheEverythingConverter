"""Image conversions powered by Pillow (+ pillow-heif for HEIC/HEIF)."""

from __future__ import annotations

from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

# Extensions we can *read*.
_READ = {
    "jpg", "jpeg", "jpe", "png", "gif", "bmp", "dib", "tif", "tiff", "webp",
    "ico", "ppm", "pgm", "pbm", "pnm", "tga", "im", "pcx", "sgi", "xbm",
    "heic", "heif", "jp2", "j2k",
}
# Extensions we can *write*.
_WRITE = {
    "jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "ico", "ppm",
    "tga", "pcx", "pdf",
}

# Pillow expects a "format" string that does not always match the extension.
_FORMAT_ALIASES = {
    "jpg": "JPEG", "jpeg": "JPEG", "jpe": "JPEG", "tif": "TIFF", "tiff": "TIFF",
    "j2k": "JPEG2000", "jp2": "JPEG2000",
}


class ImageConverter(Converter):
    name = "Pillow image converter"
    category = "Images"

    def __init__(self) -> None:
        self._pil_ok = False
        try:
            import PIL  # noqa: F401

            self._pil_ok = True
        except ImportError:
            return
        # Optional: enable HEIC/HEIF support if pillow-heif is installed.
        try:
            import pillow_heif  # type: ignore

            pillow_heif.register_heif_opener()
        except ImportError:
            self._READ_no_heif()

    def _READ_no_heif(self) -> None:
        # Without pillow-heif we cannot read HEIC/HEIF; drop them from inputs.
        for ext in ("heic", "heif"):
            _READ.discard(ext)

    def available(self) -> bool:
        return self._pil_ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self._pil_ok:
            return set()
        if normalize_ext(src_ext) in _READ:
            return set(_WRITE)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        from PIL import Image

        dst_ext = normalize_ext(dst.suffix)
        fmt = _FORMAT_ALIASES.get(dst_ext, dst_ext.upper())

        try:
            with Image.open(src) as im:
                im.load()
                save_kwargs: dict = {}

                # Formats that cannot store alpha need a flattened RGB image.
                if dst_ext in {"jpg", "jpeg", "bmp", "pcx", "ppm"}:
                    im = _flatten(im)
                elif dst_ext == "pdf":
                    im = im.convert("RGB")

                if dst_ext in {"jpg", "jpeg", "webp"}:
                    save_kwargs["quality"] = int(options.get("quality", 90))
                if dst_ext in {"jpg", "jpeg"}:
                    save_kwargs["optimize"] = True
                if dst_ext == "webp" and options.get("lossless"):
                    save_kwargs["lossless"] = True

                im.save(dst, format=fmt, **save_kwargs)
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            raise ConversionError(f"Image conversion failed: {exc}") from exc


def _flatten(im):
    """Composite an image with transparency onto a white background."""
    from PIL import Image

    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        background = Image.new("RGBA", im.size, (255, 255, 255, 255))
        background.alpha_composite(im)
        return background.convert("RGB")
    return im.convert("RGB")
