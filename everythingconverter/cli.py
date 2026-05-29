"""Command line interface for The Everything Converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converters import ConversionError, normalize_ext
from .registry import Registry


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="everythingconverter",
        description="Convert (almost) any file into (almost) any other file.",
    )
    sub = p.add_subparsers(dest="command")

    c = sub.add_parser("convert", help="Convert one or more files")
    c.add_argument("inputs", nargs="+", help="Input file(s)")
    c.add_argument("-o", "--output", help="Output file (single input only)")
    c.add_argument("-t", "--to", help="Target extension, e.g. png, mp3, pdf")
    c.add_argument("-d", "--outdir", help="Directory for outputs (with --to)")
    c.add_argument("-q", "--quality", type=int, help="Quality for lossy images (1-100)")
    c.add_argument("--bitrate", help="Audio bitrate, e.g. 192k")

    f = sub.add_parser("formats", help="List target formats for a file/extension")
    f.add_argument("source", help="A filename or bare extension (e.g. cat.jpg or jpg)")
    f.add_argument("--all", action="store_true", help="Include unavailable backends")

    sub.add_parser("doctor", help="Show which conversion backends are installed")
    sub.add_parser("gui", help="Launch the graphical interface")

    return p


def _options(args) -> dict:
    opts: dict = {}
    if getattr(args, "quality", None) is not None:
        opts["quality"] = args.quality
    if getattr(args, "bitrate", None):
        opts["audio_bitrate"] = args.bitrate
    return opts


def _cmd_convert(args, reg: Registry) -> int:
    inputs = [Path(p) for p in args.inputs]
    opts = _options(args)

    if args.output:
        if len(inputs) != 1:
            print("error: --output works with exactly one input file", file=sys.stderr)
            return 2
        dst = Path(args.output)
        return _convert_one(reg, inputs[0], dst, opts)

    if not args.to:
        print("error: provide --output or --to", file=sys.stderr)
        return 2

    to = normalize_ext(args.to)
    outdir = Path(args.outdir) if args.outdir else None
    rc = 0
    for src in inputs:
        target_dir = outdir if outdir else src.parent
        dst = target_dir / f"{src.stem}.{to}"
        rc |= _convert_one(reg, src, dst, opts)
    return rc


def _convert_one(reg: Registry, src: Path, dst: Path, opts: dict) -> int:
    try:
        reg.convert(src, dst, **opts)
        print(f"✓ {src}  ->  {dst}")
        return 0
    except ConversionError as exc:
        print(f"✗ {src}: {exc}", file=sys.stderr)
        return 1


def _cmd_formats(args, reg: Registry) -> int:
    targets = reg.targets_for(args.source)
    if not args.all:
        targets = [t for t in targets if t.available]
    if not targets:
        print(f"No conversions available from .{normalize_ext(args.source)}")
        return 1
    print(f"Targets for .{normalize_ext(args.source)}:")
    current = None
    for t in targets:
        if t.category != current:
            current = t.category
            print(f"\n  {current}:")
        flag = "" if t.available else "  (backend missing)"
        print(f"    .{t.ext}{flag}")
    return 0


def _cmd_doctor(reg: Registry) -> int:
    print("Conversion backends:\n")
    for name, category, ok in reg.backend_status():
        mark = "✓" if ok else "✗"
        print(f"  {mark}  {name:<32} [{category}]")
    print("\nMissing backends? On macOS:")
    print("  brew install ffmpeg pandoc")
    print("  brew install --cask libreoffice")
    print("  pip install pillow pillow-heif pandas openpyxl pymupdf")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    reg = Registry()

    if args.command == "convert":
        return _cmd_convert(args, reg)
    if args.command == "formats":
        return _cmd_formats(args, reg)
    if args.command == "doctor":
        return _cmd_doctor(reg)
    if args.command == "gui" or args.command is None:
        from .gui import launch

        return launch()

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
