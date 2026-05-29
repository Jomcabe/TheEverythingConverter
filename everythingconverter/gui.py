"""Tkinter GUI for The Everything Converter.

Designed to feel at home on macOS (uses ttk widgets, the system 'aqua' theme
when available, and a clean single-window layout). Supports drag-and-drop when
the optional ``tkinterdnd2`` package is installed, and always supports the
native file picker.

Workflow:
    1. Add one or more files (button or drag-and-drop).
    2. Pick a target format — the dropdown only offers formats reachable from
       *all* selected files using installed backends.
    3. (Optional) choose an output folder and quality.
    4. Convert. Each file is processed on a background thread with live status.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:  # pragma: no cover - headless / no Tk
    tk = None
    _TK_IMPORT_ERROR = exc

# Optional drag-and-drop support.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _DND = True
except Exception:  # pragma: no cover
    _DND = False

from .converters import ConversionError, normalize_ext
from .registry import Registry

APP_NAME = "The Everything Converter"


class ConverterApp:
    def __init__(self, root) -> None:
        self.root = root
        self.reg = Registry()
        self.files: list[Path] = []
        self._events: "queue.Queue[tuple]" = queue.Queue()

        root.title(APP_NAME)
        root.minsize(640, 480)
        self._init_style()
        self._build()
        self._poll_events()

    # ------------------------------------------------------------------ UI
    def _init_style(self) -> None:
        style = ttk.Style()
        if "aqua" in style.theme_names():  # native macOS look
            style.theme_use("aqua")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 8}
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Label(
            main, text=APP_NAME, font=("Helvetica", 20, "bold")
        )
        header.pack(anchor="w")
        ttk.Label(
            main,
            text="Drag in files (or click Add Files), choose a format, and convert.",
            foreground="#666",
        ).pack(anchor="w", pady=(0, 8))

        # File list
        list_frame = ttk.Frame(main)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, selectmode="extended", height=8)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)

        if _DND:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        # File buttons
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Add Files…", command=self._add_files).pack(side="left")
        ttk.Button(btns, text="Remove Selected", command=self._remove_selected).pack(
            side="left", padx=6
        )
        ttk.Button(btns, text="Clear", command=self._clear).pack(side="left")

        # Options
        opts = ttk.LabelFrame(main, text="Convert to", padding=10)
        opts.pack(fill="x", pady=12)

        row1 = ttk.Frame(opts)
        row1.pack(fill="x")
        ttk.Label(row1, text="Format:").pack(side="left")
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(
            row1, textvariable=self.format_var, state="readonly", width=14
        )
        self.format_combo.pack(side="left", padx=8)

        ttk.Label(row1, text="Quality:").pack(side="left", padx=(16, 0))
        self.quality_var = tk.IntVar(value=90)
        ttk.Spinbox(
            row1, from_=1, to=100, textvariable=self.quality_var, width=5
        ).pack(side="left", padx=8)

        row2 = ttk.Frame(opts)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Output folder:").pack(side="left")
        self.outdir_var = tk.StringVar(value="(same as source)")
        ttk.Entry(row2, textvariable=self.outdir_var, width=40).pack(
            side="left", padx=8, fill="x", expand=True
        )
        ttk.Button(row2, text="Choose…", command=self._choose_outdir).pack(side="left")

        # Action + status
        action = ttk.Frame(main)
        action.pack(fill="x")
        self.convert_btn = ttk.Button(
            action, text="Convert", command=self._start_convert
        )
        self.convert_btn.pack(side="left")
        ttk.Button(action, text="Diagnostics", command=self._show_diag).pack(
            side="left", padx=8
        )

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(12, 4))
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(main, textvariable=self.status_var, foreground="#444").pack(
            anchor="w"
        )

    # --------------------------------------------------------------- files
    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Choose files to convert")
        self._add_paths(paths)

    def _on_drop(self, event) -> None:
        # tkinterdnd2 returns a brace-wrapped, space-separated string.
        paths = self.root.tk.splitlist(event.data)
        self._add_paths(paths)

    def _add_paths(self, paths) -> None:
        added = False
        for p in paths:
            path = Path(p)
            if path.is_file() and path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", str(path))
                added = True
        if added:
            self._refresh_formats()

    def _remove_selected(self) -> None:
        for index in sorted(self.listbox.curselection(), reverse=True):
            self.listbox.delete(index)
            del self.files[index]
        self._refresh_formats()

    def _clear(self) -> None:
        self.listbox.delete(0, "end")
        self.files.clear()
        self._refresh_formats()

    def _choose_outdir(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.outdir_var.set(d)

    # ------------------------------------------------------------- formats
    def _refresh_formats(self) -> None:
        """Offer only formats reachable from *every* selected file."""
        if not self.files:
            self.format_combo["values"] = []
            self.format_var.set("")
            self.status_var.set("Ready.")
            return

        common: set[str] | None = None
        for f in self.files:
            targets = set(self.reg.available_targets(f.suffix))
            common = targets if common is None else (common & targets)
        options = sorted(common or set())

        self.format_combo["values"] = options
        if options:
            if self.format_var.get() not in options:
                self.format_var.set(options[0])
            self.status_var.set(
                f"{len(self.files)} file(s). {len(options)} target format(s) available."
            )
        else:
            self.format_var.set("")
            self.status_var.set(
                "No common target format for the selected files "
                "(or a backend is missing — see Diagnostics)."
            )

    # ------------------------------------------------------------- convert
    def _start_convert(self) -> None:
        if not self.files:
            messagebox.showinfo(APP_NAME, "Add some files first.")
            return
        target = normalize_ext(self.format_var.get())
        if not target:
            messagebox.showinfo(APP_NAME, "Choose a target format.")
            return

        outdir = self.outdir_var.get().strip()
        outdir_path = Path(outdir) if outdir and not outdir.startswith("(") else None
        options = {"quality": self.quality_var.get()}

        self.convert_btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        files = list(self.files)

        thread = threading.Thread(
            target=self._worker,
            args=(files, target, outdir_path, options),
            daemon=True,
        )
        thread.start()

    def _worker(self, files, target, outdir_path, options) -> None:
        ok = 0
        for i, src in enumerate(files, start=1):
            dst_dir = outdir_path if outdir_path else src.parent
            dst = dst_dir / f"{src.stem}.{target}"
            self._events.put(("status", f"Converting {src.name} → .{target} …"))
            try:
                self.reg.convert(src, dst, **options)
                ok += 1
                self._events.put(("log", f"✓ {src.name} → {dst.name}"))
            except ConversionError as exc:
                self._events.put(("log", f"✗ {src.name}: {exc}"))
            except Exception as exc:  # noqa: BLE001
                self._events.put(("log", f"✗ {src.name}: {exc}"))
            self._events.put(("progress", i))
        self._events.put(("done", (ok, len(files))))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "log":
                    self.status_var.set(payload)
                elif kind == "progress":
                    self.progress.config(value=payload)
                elif kind == "done":
                    ok, total = payload
                    self.convert_btn.config(state="normal")
                    self.status_var.set(f"Done. {ok}/{total} converted.")
                    if ok < total:
                        messagebox.showwarning(
                            APP_NAME,
                            f"{total - ok} file(s) failed. See status line / Diagnostics.",
                        )
                    else:
                        messagebox.showinfo(APP_NAME, f"Converted {ok} file(s).")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    # --------------------------------------------------------- diagnostics
    def _show_diag(self) -> None:
        lines = ["Conversion backends:\n"]
        for name, category, available in self.reg.backend_status():
            mark = "✓" if available else "✗ (not installed)"
            lines.append(f"{mark}  {name}  [{category}]")
        lines.append("\nTo add backends on macOS:")
        lines.append("  brew install ffmpeg pandoc")
        lines.append("  brew install --cask libreoffice")
        lines.append("  pip install pillow pillow-heif pandas openpyxl pymupdf")
        messagebox.showinfo("Diagnostics", "\n".join(lines))


def launch() -> int:
    """Create the window and run the Tk event loop. Returns a process exit code."""
    if tk is None:  # pragma: no cover
        print(
            "Tkinter is not available in this Python build.\n"
            "On macOS install Python from python.org or run: brew install python-tk\n"
            f"(import error: {_TK_IMPORT_ERROR})"
        )
        return 1

    root = TkinterDnD.Tk() if _DND else tk.Tk()
    ConverterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(launch())
