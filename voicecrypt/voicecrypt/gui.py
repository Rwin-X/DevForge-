"""Tkinter GUI for VoiceCrypt (Enroll / Encrypt / Decrypt / Verify)."""

import json
import os
import queue
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import numpy as np

from .core import (SR, MIN_ENROLL, extract_features, load_wav, create_profile,
                   estimate_stability, load_profile, recover_secret, encrypt_file,
                   read_container, decrypt_payload)

BG, PANEL, FG, MUTED, ACC = "#0e1117", "#161b22", "#e6edf3", "#8b949e", "#2f81f7"
OK_C, ERR_C = "#3fb950", "#f85149"


def apply_theme(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=BG)
    s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor="#30363d",
                lightcolor=BG, darkcolor=BG, troughcolor=PANEL, font=("Segoe UI", 10))
    s.configure("TNotebook", background=BG, borderwidth=0)
    s.configure("TNotebook.Tab", padding=(18, 9), background=PANEL, foreground=MUTED)
    s.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", FG)])
    s.configure("TLabelframe", background=BG, bordercolor="#30363d")
    s.configure("TLabelframe.Label", background=BG, foreground=MUTED)
    s.configure("TButton", padding=8, background=PANEL, foreground=FG)
    s.map("TButton", background=[("active", "#21262d"), ("disabled", PANEL)],
          foreground=[("disabled", "#555c66")])
    s.configure("Accent.TButton", background=ACC, foreground="white", font=("Segoe UI", 10, "bold"))
    s.map("Accent.TButton", background=[("active", "#1f6feb"), ("disabled", "#1b3a66")])
    s.configure("TEntry", padding=6, insertcolor=FG)
    s.configure("TSpinbox", padding=4, arrowcolor=FG, insertcolor=FG)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("H.TLabel", font=("Segoe UI", 13, "bold"))
    s.configure("Horizontal.TProgressbar", background=ACC, troughcolor=PANEL)


def safe_name(name, default="file"):
    name = Path(name).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    return name or default


class VoiceInput(ttk.LabelFrame):
    """Record from the microphone (or import a WAV) and keep voice features."""

    def __init__(self, master, multi=False):
        super().__init__(master, text=" Voice input ", padding=10)
        self.multi = multi
        self.feats = []
        self.q = queue.Queue()
        self.busy = False
        self.dur = tk.IntVar(value=5)

        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Duration (s):").pack(side="left")
        ttk.Spinbox(row, from_=3, to=20, width=4, textvariable=self.dur).pack(side="left", padx=(6, 14))
        self.b_rec = ttk.Button(row, text="●  Record", command=self.record)
        self.b_rec.pack(side="left")
        self.b_imp = ttk.Button(row, text="Import WAV…", command=self.import_wav)
        self.b_imp.pack(side="left", padx=6)
        self.b_clr = ttk.Button(row, text="Clear", command=self.clear)
        self.b_clr.pack(side="left")
        self.bar = ttk.Progressbar(self, maximum=100)
        self.bar.pack(fill="x", pady=(10, 4))
        self.status = ttk.Label(self, style="Muted.TLabel")
        self.status.pack(anchor="w")
        self._refresh()

    def latest(self):
        return self.feats[-1] if self.feats else None

    def clear(self):
        if not self.busy:
            self.feats = []
            self._refresh()

    def _refresh(self, extra=""):
        if self.multi:
            txt = f"{len(self.feats)} sample(s) collected - need at least {MIN_ENROLL}."
        else:
            txt = "Voice sample ready." if self.feats else "No voice sample yet."
        self.status.config(text=(txt + ("  " + extra if extra else "")))

    def _lock(self, locked):
        for b in (self.b_rec, self.b_imp, self.b_clr):
            b.state(["disabled"] if locked else ["!disabled"])

    def record(self):
        if self.busy:
            return
        try:
            import sounddevice as sd
        except Exception:
            messagebox.showerror("Missing dependency",
                                 "The 'sounddevice' package is required for recording.\n\n"
                                 "pip install sounddevice\n(Linux: sudo apt install libportaudio2)")
            return
        try:
            dur = max(2, min(20, int(self.dur.get())))
        except tk.TclError:
            dur = 5
        self.busy = True
        self._lock(True)
        self.t0, self.t_dur = time.time(), dur

        def work():
            try:
                a = sd.rec(int(dur * SR), samplerate=SR, channels=1, dtype="float32")
                sd.wait()
                self.q.put(("ok", a[:, 0].astype(np.float64)))
            except Exception as e:
                self.q.put(("err", e))

        threading.Thread(target=work, daemon=True).start()
        self.after(100, self._poll)

    def _poll(self):
        try:
            kind, val = self.q.get_nowait()
        except queue.Empty:
            el = time.time() - self.t0
            self.bar["value"] = min(100, 100 * el / self.t_dur)
            self.status.config(text=f"Recording... speak now ({max(0, self.t_dur - el):.0f}s left)")
            self.after(100, self._poll)
            return
        self.busy = False
        self._lock(False)
        self.bar["value"] = 0
        if kind == "err":
            messagebox.showerror("Audio error", str(val))
            self._refresh()
        else:
            self._add(val)

    def import_wav(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Import WAV file", filetypes=[("WAV audio", "*.wav")])
        if not path:
            return
        try:
            self._add(load_wav(path))
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def _add(self, audio):
        try:
            f = extract_features(audio)
        except ValueError as e:
            messagebox.showwarning("Sample rejected", str(e))
            self._refresh()
            return
        if self.multi:
            self.feats.append(f)
        else:
            self.feats = [f]
        self._refresh("(last sample accepted)")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VoiceCrypt - Voice-Bound Encryption")
        self.geometry("860x800")
        self.minsize(780, 700)
        apply_theme(self)

        self.log_box = tk.Text(self, height=8, bg=PANEL, fg=FG, relief="flat", wrap="word",
                               font=("Consolas", 9), state="disabled", padx=8, pady=6)
        self.log_box.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        self.t_enroll, self.t_enc, self.t_dec, self.t_ver = (ttk.Frame(nb, padding=16) for _ in range(4))
        nb.add(self.t_enroll, text="1  Enroll voice")
        nb.add(self.t_enc, text="2  Encrypt")
        nb.add(self.t_dec, text="3  Decrypt")
        nb.add(self.t_ver, text="Verify voice")
        self._build_enroll()
        self._build_encrypt()
        self._build_decrypt()
        self._build_verify()
        self.log("Ready. Start with 'Enroll voice' to create your voice profile.")

    # ---- helpers ----
    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def fail(self, e):
        self.log(f"ERROR: {e}")
        messagebox.showerror("Error", str(e))

    def run_bg(self, fn, done):
        q = queue.Queue()

        def work():
            try:
                q.put((True, fn()))
            except Exception as e:
                q.put((False, e))

        threading.Thread(target=work, daemon=True).start()
        self.config(cursor="watch")

        def poll():
            try:
                ok, val = q.get_nowait()
            except queue.Empty:
                self.after(80, poll)
                return
            self.config(cursor="")
            done(ok, val)

        self.after(80, poll)

    def _row(self, parent, label, var, browse=None, secret=False):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=4)
        ttk.Label(f, text=label, width=18).pack(side="left")
        ttk.Entry(f, textvariable=var, show="•" if secret else "").pack(side="left", fill="x", expand=True, padx=6)
        if browse:
            ttk.Button(f, text="Browse…", command=browse).pack(side="left")

    def _title(self, parent, title, sub):
        ttk.Label(parent, text=title, style="H.TLabel").pack(anchor="w")
        ttk.Label(parent, text=sub, style="Muted.TLabel", wraplength=780, justify="left").pack(anchor="w", pady=(2, 10))

    # ---- tab 1: enroll ----
    def _build_enroll(self):
        t = self.t_enroll
        self._title(t, "Create a voice profile",
                    f"Record at least {MIN_ENROLL} samples of the SAME phrase (a sentence of 6-8 words), "
                    "with the same microphone, in a quiet room, at natural volume and pace. "
                    "You will need to say this same phrase every time you encrypt or decrypt.")
        self.name_var = tk.StringVar(value="my-voice")
        self._row(t, "Profile name:", self.name_var)
        self.enroll_in = VoiceInput(t, multi=True)
        self.enroll_in.pack(fill="x", pady=10)
        ttk.Button(t, text="Create voice profile…", style="Accent.TButton",
                   command=self.do_enroll).pack(anchor="e", pady=6)

    def do_enroll(self):
        feats = self.enroll_in.feats
        if len(feats) < MIN_ENROLL:
            messagebox.showwarning("More samples needed", f"Record at least {MIN_ENROLL} samples first.")
            return
        name = self.name_var.get().strip() or "voice-profile"
        F = np.vstack(feats)
        profile = create_profile(F, name)
        p, succ = estimate_stability(F)
        path = filedialog.asksaveasfilename(
            title="Save voice profile", defaultextension=".vkey",
            initialfile=safe_name(name) + ".vkey", filetypes=[("VoiceCrypt profile", "*.vkey")])
        if not path:
            return
        Path(path).write_text(json.dumps(profile, indent=2))
        self.log(f"Profile saved: {path}")
        self.log(f"Estimated bit mismatch (leave-one-out): {p:.1%}   rough unlock success: {succ:.0%}")
        warn = ""
        if succ < 0.6:
            warn = ("\n\nThe voice looks unstable. Re-enroll with a quieter room, the same phrase, "
                    "and a consistent distance from the microphone.")
        messagebox.showinfo("Profile created",
                            f"Saved to:\n{path}\n\nEstimated unlock success: {succ:.0%} "
                            f"(bit mismatch {p:.1%}).{warn}")

    # ---- tab 2: encrypt ----
    def _build_encrypt(self):
        t = self.t_enc
        self._title(t, "Encrypt a file with your voice",
                    "Your voice unlocks the key bound in the profile; the passphrase is mixed in "
                    "through scrypt. AES-256-GCM protects the file.")
        self.enc_file, self.enc_prof = tk.StringVar(), tk.StringVar()
        self.enc_pw, self.enc_pw2 = tk.StringVar(), tk.StringVar()
        self._row(t, "File to encrypt:", self.enc_file,
                  lambda: self.enc_file.set(filedialog.askopenfilename() or self.enc_file.get()))
        self._row(t, "Voice profile:", self.enc_prof,
                  lambda: self.enc_prof.set(filedialog.askopenfilename(
                      filetypes=[("VoiceCrypt profile", "*.vkey")]) or self.enc_prof.get()))
        self.enc_in = VoiceInput(t)
        self.enc_in.pack(fill="x", pady=10)
        self._row(t, "Passphrase:", self.enc_pw, secret=True)
        self._row(t, "Confirm passphrase:", self.enc_pw2, secret=True)
        ttk.Button(t, text="Encrypt file", style="Accent.TButton", command=self.do_encrypt).pack(anchor="e", pady=6)

    def do_encrypt(self):
        src, pf, feat = self.enc_file.get(), self.enc_prof.get(), self.enc_in.latest()
        if not (src and os.path.isfile(src)):
            return messagebox.showwarning("Missing input", "Choose a file to encrypt.")
        if not (pf and os.path.isfile(pf)):
            return messagebox.showwarning("Missing input", "Choose your voice profile (.vkey).")
        if feat is None:
            return messagebox.showwarning("Missing input", "Record your voice (say your enrollment phrase).")
        pw = self.enc_pw.get()
        if pw != self.enc_pw2.get():
            return messagebox.showerror("Passphrase", "Passphrases do not match.")
        if not pw and not messagebox.askyesno(
                "Weak protection",
                "No passphrase set. A voice can be recorded or cloned, so the file would be "
                "protected only by your voice.\n\nContinue anyway?"):
            return
        dst = filedialog.asksaveasfilename(title="Save encrypted file", initialfile=Path(src).name + ".vcrypt",
                                           defaultextension=".vcrypt", filetypes=[("VoiceCrypt file", "*.vcrypt")])
        if not dst:
            return

        def work():
            profile = load_profile(pf)
            secret, mm = recover_secret(profile, feat)
            if secret is None:
                raise ValueError(f"Voice not recognised ({mm:.0%} of bits disagree). Say the enrollment "
                                 "phrase again, same mic and distance - or use the Verify tab to test.")
            encrypt_file(src, dst, profile, secret, pw)
            return mm

        def done(ok, val):
            if not ok:
                return self.fail(val)
            self.log(f"Encrypted -> {dst}  (voice bit mismatch {val:.1%})")
            self.enc_pw.set("")
            self.enc_pw2.set("")
            messagebox.showinfo("Done", f"Encrypted file saved:\n{dst}")

        self.run_bg(work, done)

    # ---- tab 3: decrypt ----
    def _build_decrypt(self):
        t = self.t_dec
        self._title(t, "Decrypt a .vcrypt file",
                    "Only the encrypted file is needed - the voice profile is embedded in it. "
                    "Say the same phrase and enter the same passphrase.")
        self.dec_file, self.dec_pw = tk.StringVar(), tk.StringVar()
        self._row(t, "Encrypted file:", self.dec_file,
                  lambda: self.dec_file.set(filedialog.askopenfilename(
                      filetypes=[("VoiceCrypt file", "*.vcrypt")]) or self.dec_file.get()))
        self.dec_in = VoiceInput(t)
        self.dec_in.pack(fill="x", pady=10)
        self._row(t, "Passphrase:", self.dec_pw, secret=True)
        ttk.Button(t, text="Decrypt file", style="Accent.TButton", command=self.do_decrypt).pack(anchor="e", pady=6)

    def do_decrypt(self):
        src, feat, pw = self.dec_file.get(), self.dec_in.latest(), self.dec_pw.get()
        if not (src and os.path.isfile(src)):
            return messagebox.showwarning("Missing input", "Choose a .vcrypt file.")
        if feat is None:
            return messagebox.showwarning("Missing input", "Record your voice first.")

        def work():
            meta, aad, nonce, ct = read_container(src)
            secret, mm = recover_secret(meta["profile"], feat)
            if secret is None:
                raise ValueError(f"Voice not recognised ({mm:.0%} of bits disagree).")
            name, data = decrypt_payload(meta, aad, nonce, ct, secret, pw)
            return name, data, mm

        def done(ok, val):
            if not ok:
                return self.fail(val)
            name, data, mm = val
            name = safe_name(name, "decrypted_file")
            out = filedialog.asksaveasfilename(title="Save decrypted file", initialfile=name)
            if not out:
                return
            Path(out).write_bytes(data)
            self.dec_pw.set("")
            self.log(f"Decrypted -> {out}  (voice bit mismatch {mm:.1%})")
            messagebox.showinfo("Done", f"Decrypted file saved:\n{out}")

        self.run_bg(work, done)

    # ---- tab 4: verify ----
    def _build_verify(self):
        t = self.t_ver
        self._title(t, "Test your voice against a profile",
                    "Checks whether a new recording unlocks the profile - useful for choosing a mic, "
                    "distance and phrase before you encrypt anything important.")
        self.ver_prof = tk.StringVar()
        self._row(t, "Voice profile:", self.ver_prof,
                  lambda: self.ver_prof.set(filedialog.askopenfilename(
                      filetypes=[("VoiceCrypt profile", "*.vkey")]) or self.ver_prof.get()))
        self.ver_in = VoiceInput(t)
        self.ver_in.pack(fill="x", pady=10)
        self.ver_res = ttk.Label(t, text="", font=("Segoe UI", 12, "bold"))
        self.ver_res.pack(anchor="w", pady=6)
        ttk.Button(t, text="Test voice", style="Accent.TButton", command=self.do_verify).pack(anchor="e", pady=6)

    def do_verify(self):
        pf, feat = self.ver_prof.get(), self.ver_in.latest()
        if not (pf and os.path.isfile(pf)) or feat is None:
            return messagebox.showwarning("Missing input", "Choose a profile and record your voice.")
        try:
            secret, mm = recover_secret(load_profile(pf), feat)
        except Exception as e:
            return self.fail(e)
        if secret is not None:
            self.ver_res.config(text=f"MATCH - voice accepted (bit mismatch {mm:.1%})", foreground=OK_C)
        else:
            self.ver_res.config(text=f"NO MATCH - voice rejected ({mm:.0%} bits disagree)", foreground=ERR_C)
        self.log(f"Verify: {'match' if secret is not None else 'no match'} (mismatch {mm:.1%})")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
