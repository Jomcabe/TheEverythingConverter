# Everything Converter for the web

An unlisted page at **https://jocabe.com/converter/**. The portfolio homepage has no link to it. The page sets `noindex,nofollow,noarchive`; knowing the URL still gives access.

The browser version belongs to the existing Everything Converter project. It runs all file processing on the visitor’s device, with no paid APIs, accounts, server uploads, or conversion credits. It uses the same local-first approach as the desktop tool, with additional scientific engines.

See [FORMATS.md](FORMATS.md) for the full generated input/output matrix. Multiple formats can use the same extension: select the category matching the file’s content. Counts refer to format entries and defined routes, not a promise that every file variant will convert.

## Build

```sh
cd web
npm ci
npm test
npm run build
```

Copy `web/dist/` into the portfolio repository’s `converter/` directory. Commit that directory to the branch served by GitHub Pages. Do not add a link to the homepage until the page is ready to be listed. All asset paths use `/converter/`.

## Verification

`npm test` checks registry consistency, every document reader/writer against pinned Pandoc, Unicode DOCX round trips, and actual image encoding with the pinned ImageMagick build. `npm run build -- --mode qa` includes `tests/browser.html`, which exercises real browser engines using generated, non-sensitive fixtures. Do not publish the QA build.

The browser suite verifies document/PDF output, image transcoding, tables, configuration data, numerical containers, spectroscopy, atomic coordinates, meshes, sequences, geographic data, archives, compression, audio, and subtitles. The SPA test follows SpectroChemPy’s documented single-spectrum layout; it does not establish support for every vendor layout.

## Runtime design

- `src/registry.js`: explicit conversion routes and category/format metadata.
- `src/engines.js`: browser adapters, PDF rendering/layout, local SVG rasterization, and media conversion.
- `src/wasm-worker.js`: isolated document and image engines.
- `public/python-worker.js`: lazy scientific package loading and job isolation.
- `public/scientific.py`: numerical/scientific/structured-file adapters.
- `src/app.js`: input detection, batch conversion, downloads, cancellation, and searchable catalog.

The main page stays responsive while scientific, document, image, and media engines work in workers. PDF page rendering and document layout run on the main thread. Cancellation terminates worker engines; a main-thread PDF layout/render step finishes its current browser operation before it can stop.

The first conversion in each family downloads its engine from a pinned CDN URL. Document WASM is about 58 MB, images about 15 MB, and media about 32 MB. Pyodide starts around 12 MB, then loads required packages. Network access is needed for those downloads. There is no claim of fully offline operation.

Python wheels for source-only packages are supplied locally in `public/wheels/`. They are built from pinned PyPI releases. CBOR2 is built without its C extension. JCAMP lists standard-library modules as package dependencies, so its pure wheel is installed without dependency resolution after NumPy/SciPy load.

## Limits

- Files: 128 MiB each. Expanded archives/compression: 256 MiB. Device memory can impose smaller practical limits.
- Document-to-PDF rebuilds content with PDFMake. It does not preserve exact Word or PowerPoint layouts. Unsupported embedded objects, remote images, and complex equations may be omitted or changed.
- PDF text extraction is not OCR. PDF-to-DOCX rebuilds text only. Rendered pages download in ZIP files.
- Image conversion uses the first layer/frame. SVG is rasterized locally; external references are omitted. Unsupported camera RAW delegates are not advertised.
- Tables export one worksheet/table. Spreadsheet formulas use cached results; macros and formatting are not preserved.
- Numeric containers export one selected dataset. CSV flattens higher dimensions. Units, metadata, and type precision may change. Pickled/object arrays are refused.
- Structure converters preserve supported coordinates/cell data, not all simulation settings. A structure file cannot be inferred from an experimental diffraction scan by file conversion.
- Mesh conversions depend on compatible cell types. STL/OBJ need surfaces. XDMF input must embed its data in XML.
- Proprietary spectroscopy readers support common single-spectrum layouts. Unsupported variants produce an error instead of guessed output.
- Archive links, device nodes, unsafe paths, and encrypted archives are refused. Files never execute as code.
- Legacy DOC/PPT and native CAD/instrument project formats require specialized desktop tools. No placeholder conversion options are offered for them.

## Third-party projects

See [THIRD_PARTY.md](THIRD_PARTY.md). The application’s source remains covered by the repository’s existing MIT license. The linked engines keep their own licenses.
