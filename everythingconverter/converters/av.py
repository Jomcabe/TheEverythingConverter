"""Audio and video conversions powered by ffmpeg.

ffmpeg handles a huge matrix of formats, so these converters lean on it for
everything: audio<->audio, video<->video, video->audio (extract sound), and
video->gif. ffmpeg is the single most important dependency for media work and
is trivially installed on macOS via ``brew install ffmpeg``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from .base import Converter, ConversionError, normalize_ext

AUDIO = {
    "mp3", "wav", "flac", "aac", "m4a", "ogg", "oga", "opus", "wma", "aiff",
    "aif", "alac", "ac3", "amr", "au", "caf",
}
VIDEO = {
    "mp4", "mov", "avi", "mkv", "webm", "flv", "wmv", "m4v", "mpg", "mpeg",
    "3gp", "ts", "mts", "ogv", "vob", "m2ts",
}


@lru_cache(maxsize=1)
def _ffmpeg() -> str | None:
    """Locate an ffmpeg binary.

    Resolution order:
    1. ``ECONV_FFMPEG`` environment variable (explicit override).
    2. ``ffmpeg`` on PATH (e.g. a Homebrew install).
    3. The static binary shipped by the ``imageio-ffmpeg`` package — this is
       what makes the packaged app work with zero setup on the user's machine.
    """
    override = os.environ.get("ECONV_FFMPEG")
    if override and Path(override).exists():
        return override

    found = shutil.which("ffmpeg")
    if found:
        return found

    try:
        import imageio_ffmpeg  # type: ignore

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:  # noqa: BLE001 - any failure just means "not available"
        pass
    return None


def _run_ffmpeg(args: list[str]) -> None:
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        raise ConversionError(
            "ffmpeg is required for audio/video conversion. "
            "Install it with: brew install ffmpeg"
        )
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "unknown error").strip()
        raise ConversionError(f"ffmpeg failed: {msg}")


class AudioConverter(Converter):
    name = "ffmpeg audio converter"
    category = "Audio"

    def available(self) -> bool:
        return _ffmpeg() is not None

    def outputs_for(self, src_ext: str) -> set[str]:
        if normalize_ext(src_ext) in AUDIO:
            return set(AUDIO)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        args = ["-i", str(src)]
        bitrate = options.get("audio_bitrate")
        if bitrate:
            args += ["-b:a", str(bitrate)]
        args.append(str(dst))
        _run_ffmpeg(args)


class VideoConverter(Converter):
    name = "ffmpeg video converter"
    category = "Video"

    def available(self) -> bool:
        return _ffmpeg() is not None

    def outputs_for(self, src_ext: str) -> set[str]:
        if normalize_ext(src_ext) in VIDEO:
            # video -> any video, extract to any audio, or make a gif
            return set(VIDEO) | set(AUDIO) | {"gif"}
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        dst_ext = normalize_ext(dst.suffix)

        if dst_ext == "gif":
            self._to_gif(src, dst, **options)
            return

        if dst_ext in AUDIO:
            # Strip video, keep audio only.
            args = ["-i", str(src), "-vn"]
            bitrate = options.get("audio_bitrate")
            if bitrate:
                args += ["-b:a", str(bitrate)]
            args.append(str(dst))
            _run_ffmpeg(args)
            return

        # Generic video transcode.
        args = ["-i", str(src)]
        scale = options.get("scale")  # e.g. "1280:-2"
        if scale:
            args += ["-vf", f"scale={scale}"]
        args.append(str(dst))
        _run_ffmpeg(args)

    def _to_gif(self, src: Path, dst: Path, **options) -> None:
        fps = int(options.get("fps", 12))
        width = int(options.get("gif_width", 480))
        vf = f"fps={fps},scale={width}:-1:flags=lanczos"
        _run_ffmpeg(["-i", str(src), "-vf", vf, str(dst)])


SUBTITLES = {"srt", "vtt", "ass", "ssa", "sub"}


class SubtitleConverter(Converter):
    """Convert between subtitle/caption formats (srt, vtt, ass, ...) via ffmpeg."""

    name = "ffmpeg subtitle converter"
    category = "Subtitles"

    def available(self) -> bool:
        return _ffmpeg() is not None

    def outputs_for(self, src_ext: str) -> set[str]:
        if normalize_ext(src_ext) in SUBTITLES:
            return set(SUBTITLES)
        return set()

    def convert(self, src: Path, dst: Path, **options) -> None:
        _run_ffmpeg(["-i", str(src), str(dst)])
