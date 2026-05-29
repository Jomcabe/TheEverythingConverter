"""Structured config conversions: JSON ↔ YAML ↔ TOML.

Pure-Python and bundleable. Handy for developers shuffling config files between
formats. TOML output requires a mapping at the top level (the TOML spec has no
notion of a bare top-level array/scalar)."""

from __future__ import annotations

import json
from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

_READ = {"json", "yaml", "yml", "toml"}
_WRITE = {"json", "yaml", "toml"}


class ConfigConverter(Converter):
    name = "config (json/yaml/toml) converter"
    category = "Config"

    def __init__(self) -> None:
        import importlib.util

        # PyYAML + a TOML reader/writer. tomllib is stdlib on 3.11+.
        self._yaml = importlib.util.find_spec("yaml") is not None
        self._toml_w = importlib.util.find_spec("tomli_w") is not None
        self._toml_r = (
            importlib.util.find_spec("tomllib") is not None
            or importlib.util.find_spec("tomli") is not None
        )

    def available(self) -> bool:
        return self._yaml and self._toml_w and self._toml_r

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self.available():
            return set()
        ext = normalize_ext(src_ext)
        if ext in _READ:
            # yaml/yml are equivalent on output.
            return set(_WRITE)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)
        try:
            data = self._read(src, src_ext)
            self._write(data, dst, dst_ext)
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Config conversion failed: {exc}") from exc

    def _read(self, src: Path, ext: str):
        if ext == "json":
            return json.loads(src.read_text())
        if ext in {"yaml", "yml"}:
            import yaml

            return yaml.safe_load(src.read_text())
        if ext == "toml":
            try:
                import tomllib as toml_r  # py3.11+
            except ModuleNotFoundError:
                import tomli as toml_r  # type: ignore
            with open(src, "rb") as fh:
                return toml_r.load(fh)
        raise ConversionError(f"Unsupported config input: .{ext}")

    def _write(self, data, dst: Path, ext: str) -> None:
        if ext == "json":
            dst.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        elif ext in {"yaml", "yml"}:
            import yaml

            dst.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        elif ext == "toml":
            import tomli_w

            if not isinstance(data, dict):
                raise ConversionError(
                    "TOML output requires a top-level object/mapping "
                    f"(got {type(data).__name__})."
                )
            with open(dst, "wb") as fh:
                tomli_w.dump(data, fh)
        else:
            raise ConversionError(f"Unsupported config output: .{ext}")
