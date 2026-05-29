"""Audio and video conversions powered by ffmpeg.

ffmpeg handles a huge matrix of formats, so these converters lean on it for
everything: audio<->audio, video<->video, video->audio (extract sound), and
video->gif. ffmpeg is the single most important dependency for media work and
is trivially installed on macOS via ``brew install ffmpeg``.
"""

from __future__ import annotations

import shutil
import subprocess
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


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


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
