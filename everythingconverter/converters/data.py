"""Tabular / structured data conversions powered by pandas.

Handles the common "spreadsheet & data" family: csv, tsv, json, xlsx, xls,
parquet, html tables, and xml. Any tabular input can become any tabular output.
"""

from __future__ import annotations

from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

# Inputs pandas can read into a DataFrame.
_READ = {"csv", "tsv", "json", "xlsx", "xls", "parquet", "html", "htm", "xml"}
# Outputs pandas can write a DataFrame to.
_WRITE = {"csv", "tsv", "json", "xlsx", "parquet", "html", "xml", "md"}


class DataConverter(Converter):
    name = "pandas data converter"
    category = "Data / Spreadsheets"

    def __init__(self) -> None:
        try:
            import pandas  # noqa: F401

            self._ok = True
        except ImportError:
            self._ok = False

    def available(self) -> bool:
        return self._ok

    def outputs_for(self, src_ext: str) -> set[str]:
        if not self._ok:
            return set()
        if normalize_ext(src_ext) in _READ:
            return set(_WRITE)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        import pandas as pd

        src_ext = normalize_ext(src.suffix)
        dst_ext = normalize_ext(dst.suffix)

        try:
            df = self._read(pd, src, src_ext)
            self._write(df, dst, dst_ext)
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(f"Data conversion failed: {exc}") from exc

    def _read(self, pd, src: Path, ext: str):
        if ext == "csv":
            return pd.read_csv(src)
        if ext == "tsv":
            return pd.read_csv(src, sep="\t")
        if ext == "json":
            return pd.read_json(src)
        if ext in {"xlsx", "xls"}:
            return pd.read_excel(src)
        if ext == "parquet":
            return pd.read_parquet(src)
        if ext in {"html", "htm"}:
            tables = pd.read_html(src)
            if not tables:
                raise ConversionError("No tables found in the HTML file.")
            return tables[0]
        if ext == "xml":
            return pd.read_xml(src)
        raise ConversionError(f"Unsupported data input: .{ext}")

    def _write(self, df, dst: Path, ext: str) -> None:
        if ext == "csv":
            df.to_csv(dst, index=False)
        elif ext == "tsv":
            df.to_csv(dst, sep="\t", index=False)
        elif ext == "json":
            df.to_json(dst, orient="records", indent=2)
        elif ext == "xlsx":
            df.to_excel(dst, index=False)
        elif ext == "parquet":
            df.to_parquet(dst, index=False)
        elif ext in {"html", "htm"}:
            df.to_html(dst, index=False)
        elif ext == "xml":
            df.to_xml(dst, index=False)
        elif ext == "md":
            dst.write_text(df.to_markdown(index=False))
        else:
            raise ConversionError(f"Unsupported data output: .{ext}")
