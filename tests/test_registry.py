"""Tests for the registry's discovery and dispatch logic.

These run without any heavy backend installed by using a couple of fake
converters, so the routing logic is verified deterministically.
"""

from pathlib import Path

from everythingconverter.converters.base import Converter
from everythingconverter.registry import Registry


class FakeImage(Converter):
    name = "fake image"
    category = "Images"

    def __init__(self, available=True):
        self._available = available

    def available(self):
        return self._available

    def outputs_for(self, src_ext):
        return {"png", "jpg"} if src_ext in {"png", "jpg", "bmp"} else set()

    def convert(self, src, dst, **options):
        Path(dst).write_text(f"converted {Path(src).name}")


def test_targets_for_lists_reachable_formats():
    reg = Registry([FakeImage()])
    exts = {t.ext for t in reg.targets_for("photo.bmp")}
    assert exts == {"png", "jpg"}


def test_targets_for_excludes_self():
    reg = Registry([FakeImage()])
    exts = {t.ext for t in reg.targets_for("photo.png")}
    assert "png" not in exts and "jpg" in exts


def test_find_converter_prefers_available():
    reg = Registry([FakeImage(available=False), FakeImage(available=True)])
    conv = reg.find_converter("a.bmp", "png")
    assert conv is not None and conv.available()


def test_available_targets_filters_unavailable():
    reg = Registry([FakeImage(available=False)])
    assert reg.available_targets("a.bmp") == []
    assert {t.ext for t in reg.targets_for("a.bmp")} == {"png", "jpg"}


def test_convert_runs(tmp_path):
    reg = Registry([FakeImage()])
    src = tmp_path / "x.bmp"
    src.write_bytes(b"data")
    out = reg.convert(src, tmp_path / "x.png")
    assert out.read_text().startswith("converted")
