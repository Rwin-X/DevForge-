"""
strippers.py — Backend metadata removal logic.

Handles:
    - Images (jpg, jpeg, png, tiff, webp, bmp)     -> Pillow
    - PDFs (pdf)                                    -> pypdf
    - Office Open XML (docx, xlsx, pptx)            -> zipfile (strip core/app props + custom.xml)
    - Audio (mp3, flac, ogg, wav, m4a, aac, wma)     -> mutagen
    - Generic fallback: file is copied as-is with a warning (no known metadata format)

All functions in English only; no external network calls; fully offline.
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}
PDF_EXTS = {".pdf"}
OOXML_EXTS = {".docx", ".xlsx", ".pptx"}
AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".wma"}

SUPPORTED_EXTENSIONS = IMAGE_EXTS | PDF_EXTS | OOXML_EXTS | AUDIO_EXTS


def _resolve_output_path(src_path, overwrite, output_dir):
    """
    Determine the destination path for the cleaned file.
    If overwrite is True, returns the same path (a temp file is used during
    processing, then moved into place).
    Otherwise, appends '_clean' before the extension in the same directory
    as the source file (or output_dir if provided).
    """
    src = Path(src_path)
    if overwrite:
        return str(src)

    target_dir = Path(output_dir) if output_dir else src.parent
    new_name = f"{src.stem}_clean{src.suffix}"
    return str(target_dir / new_name)


def strip_metadata(filepath, overwrite=False, output_dir=None):
    """
    Strip metadata from a single file.
    Returns (output_path, message) on success.
    Raises Exception on failure.
    """
    ext = Path(filepath).suffix.lower()

    if ext in IMAGE_EXTS:
        return _strip_image(filepath, overwrite, output_dir)
    elif ext in PDF_EXTS:
        return _strip_pdf(filepath, overwrite, output_dir)
    elif ext in OOXML_EXTS:
        return _strip_ooxml(filepath, overwrite, output_dir)
    elif ext in AUDIO_EXTS:
        return _strip_audio(filepath, overwrite, output_dir)
    else:
        return _fallback_copy(filepath, overwrite, output_dir)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def _strip_image(filepath, overwrite, output_dir):
    out_path = _resolve_output_path(filepath, overwrite, output_dir)

    with Image.open(filepath) as img:
        # Rebuild the image from raw pixel data only, dropping EXIF, ICC
        # profile, XMP, and any other embedded metadata chunks.
        data = list(img.getdata())
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(data)

        save_kwargs = {}
        fmt = img.format

        if fmt in ("JPEG", "JPG"):
            save_kwargs["quality"] = 95
            save_kwargs["optimize"] = True
        elif fmt == "PNG":
            save_kwargs["optimize"] = True

        if overwrite:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=Path(filepath).suffix)
            os.close(tmp_fd)
            clean_img.save(tmp_path, format=fmt, **save_kwargs)
            shutil.move(tmp_path, out_path)
        else:
            clean_img.save(out_path, format=fmt, **save_kwargs)

    return out_path, "stripped EXIF/ICC/XMP metadata"


# ---------------------------------------------------------------------------
# PDFs
# ---------------------------------------------------------------------------
def _strip_pdf(filepath, overwrite, output_dir):
    out_path = _resolve_output_path(filepath, overwrite, output_dir)

    reader = PdfReader(filepath)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Remove document info dictionary (Author, Title, Producer, etc.)
    writer.add_metadata({})

    # Remove XMP metadata stream if present
    try:
        writer.xmp_metadata = None
    except Exception:
        pass

    if overwrite:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        with open(tmp_path, "wb") as f:
            writer.write(f)
        shutil.move(tmp_path, out_path)
    else:
        with open(out_path, "wb") as f:
            writer.write(f)

    return out_path, "stripped document info dictionary and XMP metadata"


# ---------------------------------------------------------------------------
# Office Open XML (docx, xlsx, pptx) — these are zip archives.
# Metadata lives in docProps/core.xml, docProps/app.xml, docProps/custom.xml
# ---------------------------------------------------------------------------
def _strip_ooxml(filepath, overwrite, output_dir):
    out_path = _resolve_output_path(filepath, overwrite, output_dir)

    metadata_files = {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}
    stripped = []

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=Path(filepath).suffix)
    os.close(tmp_fd)

    with zipfile.ZipFile(filepath, "r") as zin:
        names = zin.namelist()
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                data = zin.read(name)
                if name in metadata_files:
                    stripped.append(name)
                    if name.endswith("core.xml"):
                        data = _blank_core_xml()
                    elif name.endswith("app.xml"):
                        data = _blank_app_xml()
                    elif name.endswith("custom.xml"):
                        continue  # drop custom properties entirely
                zout.writestr(name, data)

    if overwrite:
        shutil.move(tmp_path, out_path)
    else:
        shutil.move(tmp_path, out_path)

    if stripped:
        detail = "cleared " + ", ".join(stripped)
    else:
        detail = "no standard metadata parts found"
    return out_path, detail


def _blank_core_xml():
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/'
        b'package/2006/metadata/core-properties" '
        b'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        b'xmlns:dcterms="http://purl.org/dc/terms/" '
        b'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        b'</cp:coreProperties>'
    )


def _blank_app_xml():
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        b'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/'
        b'2006/extended-properties" '
        b'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/'
        b'docPropsVTypes">'
        b'</Properties>'
    )


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
def _strip_audio(filepath, overwrite, output_dir):
    out_path = _resolve_output_path(filepath, overwrite, output_dir)

    if not overwrite:
        shutil.copy2(filepath, out_path)
        target = out_path
    else:
        target = filepath

    audio = mutagen.File(target, easy=False)
    if audio is None:
        raise ValueError("unrecognized or unsupported audio format")

    if audio.tags is not None:
        audio.delete(target)
        # Reload and save to ensure tags are fully cleared on disk
        audio = mutagen.File(target, easy=False)

    if hasattr(audio, "save"):
        audio.save(target)

    return target, "stripped ID3/Vorbis/embedded audio tags"


# ---------------------------------------------------------------------------
# Fallback for unsupported types — copy unchanged, warn user
# ---------------------------------------------------------------------------
def _fallback_copy(filepath, overwrite, output_dir):
    out_path = _resolve_output_path(filepath, overwrite, output_dir)
    if not overwrite:
        shutil.copy2(filepath, out_path)
    return out_path, "WARNING: unsupported file type, copied unchanged (no metadata removed)"
