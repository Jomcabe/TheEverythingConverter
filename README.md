# The Everything Converter

Convert (almost) **any file into (almost) any other file** — images, audio,
video, documents, spreadsheets/data, PDFs, and archives — from a clean macOS
GUI or the command line.

Drop in a JPG, get a PNG. Hand it an MOV, get an MP3. Feed it a CSV, get an
XLSX, JSON, Parquet, or Markdown table. Give it a DOCX, get a PDF. It figures
out *which* engine to use and routes the conversion automatically.

---

## What it can convert

| Category | Examples | Engine |
|---|---|---|
| **Images** | jpg · png · gif · bmp · tiff · webp · ico · heic/heif · tga · pcx → any image + **PDF** | [Pillow](https://python-pillow.org) (+ pillow-heif) |
| **Audio** | mp3 · wav · flac · aac · m4a · ogg · opus · aiff · wma → any audio | [ffmpeg](https://ffmpeg.org) |
| **Video** | mp4 · mov · avi · mkv · webm · flv · wmv → any video, **extract audio**, or **GIF** | ffmpeg |
| **Documents** | md · html · docx · odt · epub · rtf · txt · tex · ppt/pptx · xls/xlsx → PDF & each other | [pandoc](https://pandoc.org) + [LibreOffice](https://libreoffice.org) |
| **PDF** | pdf → png/jpg/tiff (per page) · txt · html | [PyMuPDF](https://pymupdf.readthedocs.io) |
| **Data / Sheets** | csv · tsv · json · xlsx · xls · parquet · html · xml → each other + Markdown | [pandas](https://pandas.pydata.org) |
| **Archives** | gz ↔ bz2 ↔ xz recompression | Python stdlib |

The format matrix grows automatically as you install more backends — run
`everythingconverter doctor` to see what's active.

> Images, audio, video, PDFs, data files, and archives all work **out of the
> box** in the downloadable app (a static ffmpeg is bundled in). Only Office
> document conversion needs LibreOffice installed separately.

---

## 📦 Install (for everyone — no Python, no terminal)

Grab the ready-made app from the
[**Releases**](../../releases/latest) page and double-click:

| Your computer | Download | Then |
|---|---|---|
| **macOS** | `EverythingConverter-macOS.dmg` | Open the DMG, drag the app to **Applications**, launch it. |
| **Windows** | `EverythingConverter-Setup.exe` | Run it — installs the app and adds Start Menu / desktop shortcuts. |

That's it. Send a friend the link to your Releases page and they click once.

<details>
<summary><b>First-launch security prompt?</b> (because the app isn't code-signed)</summary>

These builds aren't signed with a paid Apple/Microsoft developer certificate,
so the OS shows a one-time warning. It's safe to bypass:

* **macOS** – right-click (or Control-click) the app → **Open** → **Open**.
  (Or System Settings → Privacy & Security → *Open Anyway*.)
* **Windows** – on the blue "Windows protected your PC" screen click
  **More info** → **Run anyway**.

To remove the prompt entirely you'd need to sign/notarize the app with paid
developer certificates.
</details>

---

## Quick start (macOS, from source)

```bash
git clone <this-repo> TheEverythingConverter
cd TheEverythingConverter
./setup.sh            # installs ffmpeg, pandoc, LibreOffice + Python deps into .venv
./run.sh              # launches the GUI
```

`setup.sh` uses [Homebrew](https://brew.sh). If you don't have it, install it
first.

### Don't want the GUI? Use the CLI

```bash
source .venv/bin/activate

# Convert and auto-name the output (cat.jpg -> cat.png)
everythingconverter convert cat.jpg --to png

# Convert to an explicit path
everythingconverter convert song.mov -o song.mp3

# Batch convert many files into a folder
everythingconverter convert *.heic --to jpg --outdir ./exported

# See every format a file can become
everythingconverter formats photo.jpg

# Check which conversion engines are installed
everythingconverter doctor
```

---

## The GUI

1. **Add files** — click *Add Files…* or drag them into the window
   (drag-and-drop needs the optional `tkinterdnd2` package).
2. **Pick a format** — the dropdown only offers formats reachable from *all*
   selected files using the backends you actually have installed.
3. **Set options** — output folder, image quality.
4. **Convert** — runs on a background thread with a live progress bar; each
   file is reported individually.

*Diagnostics* shows the status of every backend and how to install any that are
missing.

---

## Use it as a library

```python
from everythingconverter import Registry

reg = Registry()
reg.convert("cat.jpg", "cat.png")
reg.convert("data.csv", "data.xlsx")

# What can this become?
print(reg.available_targets("movie.mov"))
```

---

## Building & releasing the apps

You don't need a Mac *and* a Windows PC — **GitHub builds both for you.**

### Automatic (recommended)

Push a version tag and the [build workflow](.github/workflows/build.yml) builds
the macOS `.dmg` and the Windows installer on GitHub's runners and attaches them
to a new [Release](../../releases):

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then share the Releases page link with your friends. (You can also trigger a
build manually from the **Actions** tab → *Build desktop apps* → *Run workflow*;
that uploads the installers as downloadable artifacts without making a release.)

### Build locally

```bash
# macOS  -> dist/EverythingConverter-macOS.dmg
./packaging/build_macos.sh

# Windows (PowerShell) -> dist/EverythingConverter-Setup.exe
#   (install Inno Setup first for the one-click installer; otherwise a .zip)
.\packaging\build_windows.ps1
```

Both use [PyInstaller](https://pyinstaller.org) with
[`packaging/EverythingConverter.spec`](packaging/EverythingConverter.spec),
which bundles Python, all the pip backends, and a static ffmpeg into one
self-contained app.

---

## How it works

`everythingconverter/converters/` holds one module per backend. Each defines a
`Converter` subclass that advertises:

* `outputs_for(src_ext)` — the output extensions it can produce from a source, and
* `available()` — whether its backend is actually installed.

The **registry** (`registry.py`) merges them all into a single
"anything → anything" graph: given a source it lists every reachable target,
and given a source+target pair it picks the first *installed* converter to run
it. Missing backends are still listed (so the UI can explain what to install)
but skipped at run time.

### Adding a new converter

1. Create a class in `everythingconverter/converters/` subclassing `Converter`.
2. Implement `outputs_for`, `convert`, and `available`.
3. Register it in `registry._build_converters()`.

That's it — it instantly shows up in the GUI, the CLI, and `doctor`.

---

## Dependencies

**System tools** (installed by `setup.sh`): `ffmpeg`, `pandoc`, `LibreOffice`.
**Python packages** (`requirements.txt`): Pillow, pillow-heif, pandas, openpyxl,
pyarrow, lxml, tabulate, pymupdf, tkinterdnd2.

Everything degrades gracefully — install only the backends you need; the rest of
the converter keeps working.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests that need a particular backend skip themselves automatically when it
isn't installed.

## License

MIT
