"""Pure-Python document conversions — bundled into the app, no LibreOffice needed.

This is what lets the downloadable app convert **DOCX/Markdown/HTML/TXT → PDF**
(and between each other) out of the box. It uses small pure-Python libraries
that PyInstaller can bundle:

* ``mammoth``   – DOCX -> HTML / Markdown / plain text
* ``markdown``  – Markdown -> HTML
* ``html2text`` – HTML -> Markdown / plain text
* ``fpdf2``     – HTML / text -> PDF (with embedded DejaVu fonts for full Unicode)

When LibreOffice *is* installed it takes priority (higher fidelity for complex
Office files); these converters are the universal fallback that always works.
"""

from __future__ import annotations

import html as _htmllib
import re
import sys
from pathlib import Path

from .base import Converter, ConversionError, normalize_ext


def _find_font_dir() -> Path:
    """Locate the bundled fonts in both source and PyInstaller-packaged runs."""
    candidates = [
        Path(__file__).resolve().parent.parent / "assets" / "fonts",
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "everythingconverter" / "assets" / "fonts")
    for c in candidates:
        if (c / "DejaVuSans.ttf").exists():
            return c
    return candidates[0]


_FONT_DIR = _find_font_dir()


# ---------------------------------------------------------------------------
# Shared PDF rendering helpers (fpdf2)
# ---------------------------------------------------------------------------
def _new_pdf():
    """Create an FPDF document using the bundled Unicode font when available."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    regular = _FONT_DIR / "DejaVuSans.ttf"
    bold = _FONT_DIR / "DejaVuSans-Bold.ttf"
    if regular.exists():
        bold_path = bold if bold.exists() else regular
        pdf.add_font("DejaVu", "", str(regular))
        pdf.add_font("DejaVu", "B", str(bold_path))
        pdf.add_font("DejaVu", "I", str(regular))      # no oblique file -> reuse upright
        pdf.add_font("DejaVu", "BI", str(bold_path))
        family = "DejaVu"
    else:
        family = "Helvetica"  # core font (latin-1 only) as a last resort
    pdf.set_font(family, size=12)
    pdf.add_page()
    return pdf, family


def _strip_document_chrome(html_text: str) -> str:
    """Reduce a full HTML document to the body fragment fpdf2 renders cleanly."""
    flags = re.IGNORECASE | re.DOTALL
    html_text = re.sub(r"<!doctype[^>]*>", "", html_text, flags=flags)
    html_text = re.sub(r"<head\b.*?</head>", "", html_text, flags=flags)
    html_text = re.sub(r"</?(html|body|meta|head)\b[^>]*>", "", html_text, flags=flags)
    return html_text.strip()


def _html_to_pdf(html_text: str, dst: Path) -> None:
    # fpdf2 can't fetch base64 data-URI images; drop them so rendering succeeds.
    html_text = re.sub(
        r"<img[^>]*src=[\"']data:[^>]*>", "", html_text, flags=re.IGNORECASE
    )
    html_text = _strip_document_chrome(html_text)
    pdf, _ = _new_pdf()
    try:
        pdf.write_html(html_text)
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(f"PDF rendering failed: {exc}") from exc
    pdf.output(str(dst))


def _text_to_pdf(text: str, dst: Path) -> None:
    pdf, family = _new_pdf()
    pdf.set_font(family, size=11)
    for line in text.splitlines() or [""]:
        pdf.multi_cell(0, 6, line if line else " ")
    pdf.output(str(dst))


def _text_to_html(text: str) -> str:
    escaped = _htmllib.escape(text)
    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<pre style='font-family:monospace; white-space:pre-wrap'>{escaped}</pre>"
    )


def _html_to_markdown(html_text: str) -> str:
    import html2text

    h = html2text.HTML2Text()
    h.body_width = 0  # don't hard-wrap lines
    return h.handle(html_text)


# ---------------------------------------------------------------------------
# DOCX (Word) -> PDF / HTML / Markdown / TXT
# ---------------------------------------------------------------------------
class DocxConverter(Converter):
    name = "Word (docx) converter"
    category = "Documents"

    def __init__(self) -> None:
        self._ok = _modules_available("mammoth", "fpdf")

    def available(self) -> bool:
        return self._ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if self._ok and normalize_ext(src_ext) == "docx":
            return {"pdf", "html", "txt", "md", "markdown"}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        import mammoth

        dst_ext = normalize_ext(dst.suffix)
        try:
            with open(src, "rb") as fh:
                if dst_ext in {"md", "markdown"}:
                    dst.write_text(mammoth.convert_to_markdown(fh).value)
                elif dst_ext == "txt":
                    dst.write_text(mammoth.extract_raw_text(fh).value)
                elif dst_ext == "html":
                    dst.write_text(_wrap_html(mammoth.convert_to_html(fh).value))
                elif dst_ext == "pdf":
                    html = mammoth.convert_to_html(fh).value
                    _html_to_pdf(_wrap_html(html), dst)
                else:
                    raise ConversionError(f"Cannot convert .docx to .{dst_ext}")
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"DOCX conversion failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Markup (md / html / txt) -> PDF / HTML / Markdown / TXT
# ---------------------------------------------------------------------------
class MarkupConverter(Converter):
    name = "Markup (md/html/txt) converter"
    category = "Documents"

    _MD = {"md", "markdown"}
    _HTML = {"html", "htm"}

    def __init__(self) -> None:
        self._ok = _modules_available("markdown", "html2text", "fpdf")

    def available(self) -> bool:
        return self._ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self._ok:
            return set()
        ext = normalize_ext(src_ext)
        if ext in self._MD:
            return {"html", "pdf", "txt"}
        if ext in self._HTML:
            return {"pdf", "txt", "md", "markdown"}
        if ext == "txt":
            return {"pdf", "html", "md", "markdown"}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        import markdown as md_lib

        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)
        try:
            text = src.read_text(errors="replace")

            if src_ext in self._MD:
                html = md_lib.markdown(text, extensions=["extra", "sane_lists"])
                if dst_ext == "html":
                    dst.write_text(_wrap_html(html))
                elif dst_ext == "pdf":
                    _html_to_pdf(_wrap_html(html), dst)
                elif dst_ext == "txt":
                    dst.write_text(text)
                else:
                    raise ConversionError(f"Cannot convert markdown to .{dst_ext}")

            elif src_ext in self._HTML:
                if dst_ext == "pdf":
                    _html_to_pdf(text, dst)
                elif dst_ext in {"md", "markdown"}:
                    dst.write_text(_html_to_markdown(text))
                elif dst_ext == "txt":
                    dst.write_text(_html_to_markdown(text))
                else:
                    raise ConversionError(f"Cannot convert html to .{dst_ext}")

            elif src_ext == "txt":
                if dst_ext == "pdf":
                    _text_to_pdf(text, dst)
                elif dst_ext == "html":
                    dst.write_text(_text_to_html(text))
                elif dst_ext in {"md", "markdown"}:
                    dst.write_text(text)
                else:
                    raise ConversionError(f"Cannot convert txt to .{dst_ext}")
            else:
                raise ConversionError(f"Unsupported markup source: .{src_ext}")
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Document conversion failed: {exc}") from exc


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _wrap_html(body: str) -> str:
    if "<html" in body.lower() or "<!doctype" in body.lower():
        return body
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"


def _modules_available(*mods: str) -> bool:
    import importlib.util

    return all(importlib.util.find_spec(m) is not None for m in mods)
