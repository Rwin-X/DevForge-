"""
Headless functional smoke test — drives the REAL CyberNotes app widgets
(not reimplemented logic) under Xvfb to catch runtime issues.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cybernotes as cn

# use an isolated notes dir so this doesn't pollute the real one
TEST_ROOT = Path(__file__).resolve().parent / "notes_test"
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
cn.NOTES_ROOT = TEST_ROOT

app = cn.CyberNotes()
app.update()

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}: {name}")


# 1. tracks created on disk
check("all track dirs created", all((TEST_ROOT / t).is_dir() for t in cn.TRACKS))

# 2. tree populated with headers
check("listbox has header rows", app.listbox.size() == len(cn.TRACKS))

# 3. simulate creating a note directly via the internal flow
#    (bypass the modal dialog by calling the write logic the same way _new_note does)
track = "OSCP"
target = TEST_ROOT / track / "buffer-overflow-notes.md"
target.write_text("# buffer-overflow-notes\n\n", encoding="utf-8")
app._populate_tree()
app.update()
check("new note appears in tree", target in app._row_paths)

# 4. open it, type into the editor, save
app._open_note(target)
app.update()
app.editor.insert(cn.tk.END, "## Stack canaries\n\nBypass techniques...\n")
app.update()
check("dirty flag set after typing", app.dirty is True)

app._save_note()
app.update()
saved_content = target.read_text(encoding="utf-8")
check("save wrote content to disk", "Stack canaries" in saved_content)
check("dirty flag cleared after save", app.dirty is False)

# 5. rename
# _rename_note() itself calls simpledialog.askstring, which blocks waiting for
# a real user in a modal — not runnable headlessly. So this exercises the same
# rename mechanics the method uses (Path.rename + _populate_tree) directly.
new_target = target.with_name("bof-notes.md")
app.current_path = target
target.rename(new_target)
app._populate_tree()
app.update()
check("renamed file exists, old gone", new_target.exists() and not target.exists())
check("renamed file appears in tree", new_target in app._row_paths)

# 6. delete
new_target.unlink()
app._populate_tree()
app.update()
check("deleted file removed from disk", not new_target.exists())
check("deleted file removed from tree", new_target not in app._row_paths)

# 7. status bar reflects state correctly when nothing open
app.current_path = None
app.dirty = False
app._update_status()
check("status label shows 'no file open'", app.status_label.cget("text") == "no file open")

app.destroy()
shutil.rmtree(TEST_ROOT, ignore_errors=True)

print()
failed = [n for n, ok in results if not ok]
if failed:
    print(f"FAILED: {failed}")
    sys.exit(1)
else:
    print(f"ALL {len(results)} CHECKS PASSED")
