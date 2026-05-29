"""All built-in converters."""

from .archives import ArchiveRepackConverter, CompressionConverter
from .av import AudioConverter, SubtitleConverter, VideoConverter
from .base import Converter, ConversionError, normalize_ext
from .config import ConfigConverter
from .data import DataConverter
from .documents import LibreOfficeConverter, PandocConverter
from .images import ImageConverter
from .pdf import PdfConverter
from .textdocs import DocxConverter, MarkupConverter
from .vector import SvgConverter

__all__ = [
    "Converter",
    "ConversionError",
    "normalize_ext",
    "ImageConverter",
    "SvgConverter",
    "AudioConverter",
    "VideoConverter",
    "SubtitleConverter",
    "DataConverter",
    "ConfigConverter",
    "PandocConverter",
    "LibreOfficeConverter",
    "DocxConverter",
    "MarkupConverter",
    "PdfConverter",
    "CompressionConverter",
    "ArchiveRepackConverter",
]
