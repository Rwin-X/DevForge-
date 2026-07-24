# METASTRIP

Minimal GUI tool to strip embedded metadata from files. Drag-and-drop or
multi-select files, then remove EXIF, XMP, ICC, document properties, and
audio tags in one click. Fully offline — no network calls.

## Supported file types

| Type    | Extensions                                  | What gets stripped                          |
|---------|----------------------------------------------|----------------------------------------------|
| Images  | .jpg .jpeg .png .tiff .tif .webp .bmp        | EXIF, ICC profile, XMP, text chunks           |
| PDF     | .pdf                                          | Info dictionary (Author/Title/etc), XMP       |
| Office  | .docx .xlsx .pptx                             | core.xml, app.xml, custom.xml properties      |
| Audio   | .mp3 .flac .ogg .wav .m4a .aac .wma           | ID3 / Vorbis comments / embedded tags         |

Unsupported file types are copied unchanged with a warning (no metadata
format is known for them, so nothing is touched).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python3 metastrip.py
```

## Usage

1. Drag files (or whole folders) into the drop zone, or click **BROWSE FILES**.
2. Optionally check **Overwrite original files** — if left unchecked, cleaned
   copies are saved next to the originals with a `_clean` suffix.
3. Click **▶ STRIP METADATA**.
4. Check the log panel for a per-file summary of what was removed.

## Notes

- Images are rebuilt from raw pixel data only, so all metadata chunks are
  dropped regardless of format quirks.
- PDF stripping clears the Info dictionary and XMP stream but keeps page
  content untouched.
- Office files (docx/xlsx/pptx) are zip archives — this tool rewrites the
  `docProps/` metadata parts and leaves the rest of the archive intact.
- For audio, tags are fully deleted and the file is re-saved; audio data
  itself is not re-encoded.
