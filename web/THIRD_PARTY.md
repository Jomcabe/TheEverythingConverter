# Third-party conversion engines

The web frontend links to these independently licensed open-source projects. CDN-hosted binaries and lazy packages retain their original licenses and source links. Dependency versions are pinned in `package-lock.json` and `public/python-worker.js`.

| Project | Purpose | License / source |
| --- | --- | --- |
| Pandoc / pandoc-wasm | Documents, markup, bibliography | [GPL-2.0-or-later](https://github.com/jgm/pandoc), [wrapper](https://github.com/pandoc/pandoc-wasm) |
| ImageMagick / magick-wasm | Raster conversion | [ImageMagick License](https://github.com/ImageMagick/ImageMagick), [Apache-2.0 wrapper](https://github.com/dlemstra/magick-wasm) |
| FFmpeg / ffmpeg.wasm | Audio, video, subtitles | [FFmpeg licensing](https://ffmpeg.org/legal.html), [MIT wrapper](https://github.com/ffmpegwasm/ffmpeg.wasm). The distributed core includes GPL codecs. |
| Pyodide | Python in WebAssembly | [MPL-2.0](https://github.com/pyodide/pyodide), packaged libraries carry separate licenses |
| PDF.js | PDF reading/rendering | [Apache-2.0](https://github.com/mozilla/pdf.js) |
| PDFMake | PDF creation and bundled fonts | [MIT](https://github.com/bpampuch/pdfmake), bundled Roboto fonts use Apache-2.0 |
| pdf-lib | Image-to-PDF | [MIT](https://github.com/Hopding/pdf-lib) |
| html-to-pdfmake | HTML layout adapter | [MIT](https://github.com/Aymkdn/html-to-pdfmake) |
| DOMPurify | Sanitizing document/SVG content | [Apache-2.0 or MPL-2.0](https://github.com/cure53/DOMPurify) |
| fflate | Local ZIP creation | [MIT](https://github.com/101arrowz/fflate) |
| NumPy, SciPy, pandas | Numerical and tabular data | [NumPy](https://github.com/numpy/numpy), [SciPy](https://github.com/scipy/scipy), [pandas](https://github.com/pandas-dev/pandas) |
| h5py, netCDF4, Astropy | Scientific containers | [h5py](https://github.com/h5py/h5py), [netCDF4](https://github.com/Unidata/netcdf4-python), [Astropy](https://github.com/astropy/astropy) |
| ASE | Crystal and atomic structures | [LGPL-2.1-or-later](https://gitlab.com/ase/ase) |
| meshio | Mesh formats | [MIT](https://github.com/nschloe/meshio) |
| Biopython | Sequence formats | [Biopython license](https://github.com/biopython/biopython) |
| Shapely | Geographic geometry | [BSD-3-Clause](https://github.com/shapely/shapely) |
| FontTools | Font containers | [MIT](https://github.com/fonttools/fonttools) |
| SPC Spectra 0.4.0 | Galactic SPC reader | [Original source](https://github.com/nick-macro/spc-spectra); the wheel retains upstream metadata |
| JCAMP 1.3.0 | JCAMP-DX reader | [MIT](https://github.com/nzhagen/jcamp) |
| ODFPy 1.4.1 | OpenDocument spreadsheets | [Apache-2.0 / GPL-2.0 / LGPL-2.1](https://github.com/eea/odfpy), see the wheel’s included license files |
| CBOR2 5.6.5 | CBOR serialization | [MIT](https://github.com/agronholm/cbor2) |

OMNIC SPA directory/axis interpretation follows the [SpectroChemPy format documentation](https://www.spectrochempy.fr/1.3.0/devguide/file_formats/omnic/spa.html). The small bounded reader is implemented independently from that documented layout.
