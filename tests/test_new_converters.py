"""Tests for the document / config / svg / subtitle / archive converters.

DOCX and markup conversions are tested via a registry that excludes LibreOffice
and pandoc, exercising the pure-Python path that the packaged app ships with.
Each test skips itself if the relevant backend isn't installed.
"""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from everythingconverter.converters import (
    ArchiveRepackConverter,
    ConfigConverter,
    DocxConverter,
    MarkupConverter,
    SvgConverter,
)
from everythingconverter.registry import Registry


def _have(*mods: str) -> bool:
    return all(importlib.util.find_spec(m) is not None for m in mods)


# Pure-Python document registry (no LibreOffice / pandoc), like the shipped app.
pure = Registry([MarkupConverter(), DocxConverter()])


@pytest.mark.skipif(not _have("markdown", "fpdf"), reason="markdown/fpdf2 missing")
def test_markdown_to_pdf(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("# Title\n\nBody with **bold** and unicode café.\n")
    out = pure.convert(src, tmp_path / "a.pdf")
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"


@pytest.mark.skipif(not _have("markdown"), reason="markdown missing")
def test_markdown_to_html(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("# Hi\n\n- one\n- two\n")
    out = pure.convert(src, tmp_path / "a.html")
    body = out.read_text()
    assert "<h1>" in body and "<li>" in body


@pytest.mark.skipif(not _have("mammoth", "fpdf", "docx"), reason="docx tools missing")
def test_docx_to_pdf_and_text(tmp_path):
    import docx

    d = docx.Document()
    d.add_heading("Report", level=1)
    d.add_paragraph("Unicode: café — résumé “quote”.")
    src = tmp_path / "r.docx"
    d.save(src)

    pdf = pure.convert(src, tmp_path / "r.pdf")
    assert pdf.read_bytes()[:4] == b"%PDF"

    txt = pure.convert(src, tmp_path / "r.txt")
    assert "café" in txt.read_text()


@pytest.mark.skipif(not _have("yaml", "tomli_w"), reason="pyyaml/tomli_w missing")
def test_config_json_yaml_toml_roundtrip(tmp_path):
    reg = Registry([ConfigConverter()])
    data = {"name": "app", "port": 8080, "nested": {"x": [1, 2]}}
    src = tmp_path / "c.json"
    src.write_text(json.dumps(data))

    yaml_out = reg.convert(src, tmp_path / "c.yaml")
    toml_out = reg.convert(src, tmp_path / "c.toml")
    assert "name: app" in yaml_out.read_text()
    assert 'name = "app"' in toml_out.read_text()

    back = reg.convert(yaml_out, tmp_path / "back.json")
    assert json.loads(back.read_text()) == data


@pytest.mark.skipif(not _have("yaml", "tomli_w"), reason="pyyaml/tomli_w missing")
def test_config_toplevel_array_to_toml_errors(tmp_path):
    from everythingconverter.converters import ConversionError

    reg = Registry([ConfigConverter()])
    src = tmp_path / "list.json"
    src.write_text("[1, 2, 3]")
    with pytest.raises(ConversionError):
        reg.convert(src, tmp_path / "list.toml")


@pytest.mark.skipif(not _have("svglib", "reportlab"), reason="svglib missing")
def test_svg_to_png_and_pdf(tmp_path):
    reg = Registry([SvgConverter()])
    src = tmp_path / "s.svg"
    src.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
        '<rect width="40" height="40" fill="red"/></svg>'
    )
    png = reg.convert(src, tmp_path / "s.png")
    pdf = reg.convert(src, tmp_path / "s.pdf")
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert pdf.read_bytes()[:4] == b"%PDF"


def test_archive_zip_to_tar_roundtrip(tmp_path):
    import tarfile

    reg = Registry([ArchiveRepackConverter()])
    src = tmp_path / "a.zip"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("dir/one.txt", "one")
        zf.writestr("two.txt", "two")

    tgz = reg.convert(src, tmp_path / "a.tgz")
    with tarfile.open(tgz) as tf:
        assert set(tf.getnames()) == {"dir/one.txt", "two.txt"}
