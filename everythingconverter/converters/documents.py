"""Document conversions via pandoc and LibreOffice.

Two complementary backends:

* **pandoc** – best for lightweight/markup documents (markdown, html, rst,
  latex, epub, docx, odt, txt, rtf, ...).
* **LibreOffice** (``soffice --headless``) – best for office formats and for
  producing PDFs (doc/docx/odt/ppt/pptx/xls/xlsx -> pdf, and between office
  formats). Comes pre-installed on many systems; on macOS install the
  LibreOffice app.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

# ---------------------------------------------------------------------------
# pandoc
# ---------------------------------------------------------------------------
_PANDOC_READ = {
    "md", "markdown", "html", "htm", "docx", "odt", "epub", "rst", "tex",
    "latex", "txt", "rtf", "org", "json", "csv",
}
_PANDOC_WRITE = {
    "md", "markdown", "html", "docx", "odt", "epub", "rst", "tex", "latex",
    "txt", "rtf", "org",
}
# Pandoc's "to" name differs from the extension in a few cases.
_PANDOC_TO = {"md": "markdown", "tex": "latex", "txt": "plain", "htm": "html"}
_PANDOC_FROM = {"md": "markdown", "tex": "latex", "htm": "html", "txt": "markdown"}


class PandocConverter(Converter):
    name = "pandoc document converter"
    category = "Documents"

    def available(self) -> bool:
        return shutil.which("pandoc") is not None

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self.available():
            return set()
        if normalize_ext(src_ext) in _PANDOC_READ:
            return set(_PANDOC_WRITE)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        pandoc = shutil.which("pandoc")
        if not pandoc:
            raise ConversionError("pandoc is not installed. Install with: brew install pandoc")

        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)
        args = [pandoc, str(src)]
        frm = _PANDOC_FROM.get(src_ext)
        if frm:
            args += ["-f", frm]
        to = _PANDOC_TO.get(dst_ext)
        if to:
            args += ["-t", to]
        if dst_ext in {"html", "htm"}:
            args.append("--standalone")
        args += ["-o", str(dst)]

        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ConversionError(f"pandoc failed: {(proc.stderr or proc.stdout).strip()}")


# ---------------------------------------------------------------------------
# LibreOffice
# ---------------------------------------------------------------------------
_OFFICE_READ = {
    "doc", "docx", "odt", "rtf", "txt", "html", "htm", "ppt", "pptx", "odp",
    "xls", "xlsx", "ods", "csv", "md",
}
_OFFICE_WRITE = {
    "pdf", "docx", "odt", "rtf", "txt", "html", "ppt", "pptx", "odp", "xls",
    "xlsx", "ods", "csv",
}


def _soffice() -> str | None:
    for candidate in ("soffice", "libreoffice"):
        path = shutil.which(candidate)
        if path:
            return path
    # Typical macOS install location.
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return str(mac) if mac.exists() else None


class LibreOfficeConverter(Converter):
    name = "LibreOffice document converter"
    category = "Documents"

    def available(self) -> bool:
        return _soffice() is not None

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self.available():
            return set()
        if normalize_ext(src_ext) in _OFFICE_READ:
            return set(_OFFICE_WRITE)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        soffice = _soffice()
        if not soffice:
            raise ConversionError(
                "LibreOffice is not installed. Get it from libreoffice.org "
                "(or 'brew install --cask libreoffice')."
            )
        dst_ext = normalize_ext(dst.suffix)

        with tempfile.TemporaryDirectory() as tmp:
            args = [
                soffice, "--headless", "--convert-to", dst_ext,
                "--outdir", tmp, str(src),
            ]
            proc = subprocess.run(args, capture_output=True, text=True)
            if proc.returncode != 0:
                raise ConversionError(
                    f"LibreOffice failed: {(proc.stderr or proc.stdout).strip()}"
                )
            produced = Path(tmp) / f"{src.stem}.{dst_ext}"
            if not produced.exists():
                # LibreOffice occasionally picks a different extension; grab any output.
                outputs = list(Path(tmp).iterdir())
                if not outputs:
                    raise ConversionError("LibreOffice produced no output file.")
                produced = outputs[0]
            shutil.move(str(produced), str(dst))
