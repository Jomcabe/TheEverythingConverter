"""Real end-to-end conversion tests, skipped when a backend is missing."""

import importlib.util

import pytest

from everythingconverter.registry import Registry

reg = Registry()


def _have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


@pytest.mark.skipif(not _have("PIL"), reason="Pillow not installed")
def test_image_jpg_to_png(tmp_path):
    from PIL import Image

    src = tmp_path / "in.jpg"
    Image.new("RGB", (32, 24), (200, 100, 50)).save(src)

    out = reg.convert(src, tmp_path / "out.png")
    assert out.exists()
    with Image.open(out) as im:
        assert im.format == "PNG"
        assert im.size == (32, 24)


@pytest.mark.skipif(not _have("PIL"), reason="Pillow not installed")
def test_image_png_alpha_to_jpg_flattens(tmp_path):
    from PIL import Image

    src = tmp_path / "in.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(src)

    out = reg.convert(src, tmp_path / "out.jpg", quality=85)
    with Image.open(out) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"


@pytest.mark.skipif(not _have("PIL"), reason="Pillow not installed")
def test_image_to_pdf(tmp_path):
    from PIL import Image

    src = tmp_path / "in.png"
    Image.new("RGB", (16, 16), (10, 20, 30)).save(src)
    out = reg.convert(src, tmp_path / "out.pdf")
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.skipif(not _have("pandas"), reason="pandas not installed")
def test_csv_to_json(tmp_path):
    import json

    src = tmp_path / "in.csv"
    src.write_text("name,age\nAda,36\nLin,29\n")
    out = reg.convert(src, tmp_path / "out.json")
    data = json.loads(out.read_text())
    assert data == [{"name": "Ada", "age": 36}, {"name": "Lin", "age": 29}]


@pytest.mark.skipif(
    not (_have("pandas") and _have("openpyxl")), reason="pandas/openpyxl missing"
)
def test_csv_to_xlsx_and_back(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("a,b\n1,2\n3,4\n")
    xlsx = reg.convert(src, tmp_path / "out.xlsx")
    assert xlsx.exists()
    back = reg.convert(xlsx, tmp_path / "back.csv")
    assert "a,b" in back.read_text()
