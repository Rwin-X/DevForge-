"""
counter_core.py
Core line-counting logic for LOC Counter — separated from the GUI layer
so it can be unit-tested and reused headlessly (e.g. from a CLI).
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# --------------------------------------------------------------------------
# Language / extension registry
# --------------------------------------------------------------------------
# Maps a human-readable language name -> set of file extensions (lowercase,
# including the leading dot) that count toward it.
LANGUAGE_EXTENSIONS: Dict[str, Set[str]] = {
    "Python":        {".py", ".pyw", ".pyi"},
    "JavaScript":    {".js", ".jsx", ".mjs", ".cjs"},
    "TypeScript":    {".ts", ".tsx"},
    "C":             {".c", ".h"},
    "C++":           {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"},
    "C#":            {".cs"},
    "Java":          {".java"},
    "Go":            {".go"},
    "Rust":          {".rs"},
    "Ruby":          {".rb"},
    "PHP":           {".php"},
    "Swift":         {".swift"},
    "Kotlin":        {".kt", ".kts"},
    "Shell":         {".sh", ".bash", ".zsh"},
    "PowerShell":    {".ps1", ".psm1"},
    "HTML":          {".html", ".htm"},
    "CSS":           {".css", ".scss", ".sass", ".less"},
    "SQL":           {".sql"},
    "YAML":          {".yml", ".yaml"},
    "JSON":          {".json"},
    "XML":           {".xml"},
    "Markdown":      {".md", ".markdown"},
    "Lua":           {".lua"},
    "Perl":          {".pl", ".pm"},
    "R":             {".r"},
    "Dart":          {".dart"},
    "Scala":         {".scala"},
    "Assembly":      {".asm", ".s"},
}

# Reverse lookup: extension -> language name
EXT_TO_LANGUAGE: Dict[str, str] = {
    ext: lang for lang, exts in LANGUAGE_EXTENSIONS.items() for ext in exts
}

# Directories that are near-universally junk for LOC purposes.
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git", ".svn", ".hg", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", "venv", ".venv", "env", ".env", "build", "dist",
    ".idea", ".vscode", "target", ".tox", "site-packages", ".ruff_cache",
}


@dataclass
class FileResult:
    path: str
    language: str
    total_lines: int
    blank_lines: int
    code_lines: int  # total_lines - blank_lines (comment stripping not attempted; see note in GUI)


@dataclass
class ScanResult:
    files: List[FileResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)  # "path: reason"

    def by_language(self) -> Dict[str, Dict[str, int]]:
        """Aggregate totals per language: {'Python': {'files': N, 'total_lines': N, 'code_lines': N, 'blank_lines': N}}"""
        agg: Dict[str, Dict[str, int]] = {}
        for f in self.files:
            slot = agg.setdefault(
                f.language, {"files": 0, "total_lines": 0, "code_lines": 0, "blank_lines": 0}
            )
            slot["files"] += 1
            slot["total_lines"] += f.total_lines
            slot["code_lines"] += f.code_lines
            slot["blank_lines"] += f.blank_lines
        return agg

    def grand_total(self) -> Dict[str, int]:
        total = {"files": 0, "total_lines": 0, "code_lines": 0, "blank_lines": 0}
        for f in self.files:
            total["files"] += 1
            total["total_lines"] += f.total_lines
            total["code_lines"] += f.code_lines
            total["blank_lines"] += f.blank_lines
        return total


def count_lines_in_file(path: str) -> Optional[FileResult]:
    """
    Read a file and count total/blank/code lines.
    Returns None (with the caller expected to log) only on decode failure;
    other IO errors propagate as exceptions for the caller to catch.
    """
    ext = os.path.splitext(path)[1].lower()
    language = EXT_TO_LANGUAGE.get(ext)
    if language is None:
        return None

    # Try utf-8 first, fall back to latin-1 (never fails, but may mangle
    # non-ASCII text — acceptable for a line-count tool).
    text = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as fh:
                text = fh.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        return None

    lines = text.splitlines()
    total = len(lines)
    blank = sum(1 for line in lines if line.strip() == "")
    code = total - blank

    return FileResult(
        path=path,
        language=language,
        total_lines=total,
        blank_lines=blank,
        code_lines=code,
    )


def scan_directory(
    root: str,
    selected_languages: Optional[Set[str]] = None,
    excluded_dirs: Optional[Set[str]] = None,
    follow_symlinks: bool = False,
) -> ScanResult:
    """
    Walk `root` recursively and count lines for every recognized source file.

    selected_languages: if provided, only these language names are counted
                         (others are skipped entirely). None = all known languages.
    excluded_dirs:       directory *names* (not paths) to prune from the walk.
                         Defaults to DEFAULT_EXCLUDED_DIRS if None.
    """
    if excluded_dirs is None:
        excluded_dirs = DEFAULT_EXCLUDED_DIRS

    if selected_languages is not None:
        allowed_exts = {
            ext for lang in selected_languages for ext in LANGUAGE_EXTENSIONS.get(lang, set())
        }
    else:
        allowed_exts = set(EXT_TO_LANGUAGE.keys())

    result = ScanResult()

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        # Prune excluded directories in-place so os.walk doesn't descend into them.
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs]

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in allowed_exts:
                continue

            full_path = os.path.join(dirpath, fname)
            try:
                fr = count_lines_in_file(full_path)
            except OSError as e:
                result.errors.append(f"{full_path}: {e}")
                continue

            if fr is not None:
                result.files.append(fr)

    return result
