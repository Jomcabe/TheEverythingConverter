# Verification, 23 November 2026

- Production Vite build succeeds.
- Five automated Node checks pass: registry integrity (including no duplicate routes), compound extensions, all document readers/writers against pinned Pandoc, Unicode DOCX round trip, and real encoding with every advertised image writer.
- All **25 real browser checks pass** in Chromium: Markdown → DOCX → PDF → extracted text; PDF → PNG ZIP; Markdown → PPTX → PDF; PNG ↔ WebP; SVG → PNG; PNG → SVGZ → PNG; CSV ↔ XLSX; CSV → Parquet → JSON; CSV ↔ ODS; JSON ↔ CBOR; JSON → YAML → TOML; CSV ↔ NPY; CSV → MAT → HDF5 → CSV; CSV ↔ NetCDF; XRDML → CSV; documented OMNIC SPA → CSV; XY → JCAMP → CSV; XYZ ↔ CIF; OFF → STL; FASTA → GenBank; GeoJSON ↔ KML; ZIP ↔ TAR.GZ; Gzip → XZ → decompressed bytes; WAV → MP3; SRT → VTT.
- Additional native Python checks confirm the independently documented SPA directory/descending X-axis, reject archive traversal paths, and refuse NumPy object/pickle payloads.
- Browser layout and scientific quick-selection controls were visually reviewed.
- No edits to the portfolio homepage, navigation, CNAME, or site-wide branding are part of this change.

These are representative conversions, not exhaustive tests of every route or every proprietary file variant. Each route exposes format/metadata/fidelity limits in the interface. A file may still fail if it uses unsupported codecs, proprietary variations, incompatible cell types, encryption, or more memory than its browser can provide.
