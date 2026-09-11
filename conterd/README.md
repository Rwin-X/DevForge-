# LOC Counter

A GUI tool for recursively scanning a folder and counting lines of code by programming language.

## Usage

```bash
python3 loc_counter_gui.py
```

Uses only the Python standard library (`tkinter`). If you encounter the error:

`ModuleNotFoundError: No module named 'tkinter'`

Install it using the appropriate command:

* **Ubuntu/Debian:** `sudo apt install python3-tk`
* **Fedora:** `sudo dnf install python3-tkinter`
* **Arch:** `sudo pacman -S tk`
* **macOS (python.org installer):** tkinter is included by default
* **Windows:** tkinter is included with the standard Python installation from python.org

## Features

* Select a folder through a file dialog or enter a path manually
* Separate counting for ~25 common programming languages/formats (Python, JS/TS, C/C++, Go, Rust, Java, Shell, ...)
* Enable or disable individual languages before scanning
* Automatically ignore unnecessary directories (`.git`, `node_modules`, `venv`, `__pycache__`, ...) — can be disabled
* Reports include: file count, code lines, blank lines, and total lines — broken down by language and overall totals
* CSV export
* Scanning runs in a separate thread so the UI does not freeze while scanning large folders
* Reading errors (such as `permission denied`) are reported separately

## File Structure

* `counter_core.py` — Core counting logic (GUI-independent and independently testable)
* `loc_counter_gui.py` — GUI layer (`tkinter/ttk`)

## Note About "Lines of Code"

The current implementation subtracts blank lines from the total number of lines to calculate `code_lines`.

However, comments are not separated because accurately detecting comments for every programming language requires a language-specific parser, which would go beyond the scope of a general-purpose tool.

If comment separation is required, comment rules (`#`, `//`, `/* */`, ...) should be added for each language.

## Adding a New Language

In `counter_core.py`, edit the `LANGUAGE_EXTENSIONS` dictionary:

```python
LANGUAGE_EXTENSIONS["Zig"] = {".zig"}
```
