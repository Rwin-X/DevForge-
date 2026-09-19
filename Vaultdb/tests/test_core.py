"""Headless tests for the storage + encryption layer. Run: python tests/test_core.py"""
import base64, importlib.util, json, os, struct, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import *
import core

FAST = KdfParams(n_log2=12, r=8, p=1)     # fast params so the test suite runs quickly
d = tempfile.mkdtemp()
P = lambda n: os.path.join(d, n)
ok = lambda m: print("  ok  ", m)

# ---- 1. v2 create, no plaintext on disk, header + ciphertext structure
v = Vault.create(P("a.vdb"), "secret-pw", FAST)
v.add_text("hello", "world body", "a,b"); v.set_kv("k", "v")
src = P("f.bin"); open(src, "wb").write(os.urandom(5000)); fid = v.add_file(src)
v.save(); v.close()
raw = open(P("a.vdb"), "rb").read()
assert raw.startswith(MAGIC_V2)
assert b"world body" not in raw and b"SQLite" not in raw and b"hello" not in raw
ok("v2 container: magic present, no plaintext on disk")

# ---- 2. wrong password / right password / roundtrip
try: Vault.open(P("a.vdb"), "nope"); raise SystemExit("FAIL")
except WrongPasswordError: ok("wrong password rejected")
try: Vault.open(P("a.vdb")); raise SystemExit("FAIL")
except WrongPasswordError: ok("missing password rejected")
v = Vault.open(P("a.vdb"), "secret-pw")
assert v.list_texts()[0][1] == "hello" and v.list_kv()[0][0] == "k"
out = P("out.bin"); v.export_file(fid, out)
assert open(out, "rb").read() == open(src, "rb").read()
ok("reopen + binary file roundtrip")

# ---- 3. nonce is fresh on every save (same key + reused nonce would break GCM)
v.save(); n1 = open(P("a.vdb"), "rb").read()[25:37]
v.save(); n2 = open(P("a.vdb"), "rb").read()[25:37]
assert n1 != n2
ok("fresh random nonce on every save")

# ---- 4. tamper detection: flip a bit in EVERY region (magic excluded, it selects the format)
good = open(P("a.vdb"), "rb").read()
regions = {"kdf params": 6, "salt": 12, "nonce": 30, "ciphertext": 60, "tag": len(good) - 3}
for name, pos in regions.items():
    b = bytearray(good); b[pos] ^= 1
    open(P("t.vdb"), "wb").write(b)
    try: Vault.open(P("t.vdb"), "secret-pw"); raise SystemExit(f"FAIL tamper {name}")
    except (WrongPasswordError, NotAVaultError): pass
ok("tampering detected in: " + ", ".join(regions))

# ---- 5. hostile KDF params (memory-exhaustion DoS) are refused BEFORE deriving a key
b = bytearray(good); b[6] = 40
open(P("dos.vdb"), "wb").write(b)
try: Vault.open(P("dos.vdb"), "x"); raise SystemExit("FAIL dos")
except NotAVaultError: ok("absurd scrypt parameters refused")
open(P("trunc.vdb"), "wb").write(good[:20])
try: Vault.open(P("trunc.vdb"), "x"); raise SystemExit("FAIL trunc")
except NotAVaultError: ok("truncated file refused")

# ---- 6. backup: previous good copy kept as .bak
v.add_text("second", "x"); v.save()
assert os.path.exists(P("a.vdb.bak"))
bak = Vault.open(P("a.vdb.bak"), "secret-pw")
assert bak.stats().texts == 1 and v.stats().texts == 2
bak.close()
ok(".bak holds the previous version, main file holds the new one")

# ---- 7. re-key
v.set_password("new-pw", FAST); v.close()
try: Vault.open(P("a.vdb"), "secret-pw"); raise SystemExit("FAIL")
except WrongPasswordError: ok("old password rejected after re-key")
v = Vault.open(P("a.vdb"), "new-pw"); assert v.stats().texts == 2

# ---- 8. remove encryption -> plain SQLite; reopen without password
v.remove_password(); v.close()
assert not is_encrypted_container(P("a.vdb"))
v = Vault.open(P("a.vdb")); assert v.stats().texts == 2
ok("re-key + remove encryption")

# ---- 9. search escapes wildcards
v.add_text("100% done", "snake_case"); v.add_text("other", "zzz")
assert [r[1] for r in v.list_texts("%")] == ["100% done"]
assert [r[1] for r in v.list_texts("_")] == ["100% done"]
assert len(v.list_texts("")) == 4
ok("LIKE wildcards % and _ are matched literally")

# ---- 10. JSON export/import roundtrip (with binary file)
v.export_json(P("e.json"))
j = json.load(open(P("e.json"), encoding="utf-8"))
assert j["format"] == "vaultdb-export" and len(j["notes"]) == 4
w = Vault.create(P("w.vdb"))
c = w.import_json(P("e.json"))
assert c == {"notes": 4, "data": 1, "files": 1}, c
fid2 = w._conn.execute("SELECT id FROM file_entries").fetchone()[0]
w.export_file(fid2, P("out2.bin"))
assert open(P("out2.bin"), "rb").read() == open(src, "rb").read()
ok("JSON export -> import roundtrip incl. binary file")

# ---- 11. import rejects garbage and rolls back atomically
open(P("bad.json"), "w").write("{not json")
try: w.import_json(P("bad.json")); raise SystemExit("FAIL")
except VaultError: pass
open(P("bad2.json"), "w").write(json.dumps({"format": "other"}))
try: w.import_json(P("bad2.json")); raise SystemExit("FAIL")
except VaultError: pass
before = w.stats()
open(P("bad3.json"), "w").write(json.dumps({"format": "vaultdb-export", "notes": [{"title": "will-rollback"}],
                                             "files": [{"name": "x", "data_base64": "!!!notbase64!!!"}]}))
try: w.import_json(P("bad3.json")); raise SystemExit("FAIL")
except VaultError: pass
assert w.stats() == before
ok("import rejects garbage; a failed import leaves the database unchanged")

# ---- 12. BACKWARD COMPAT: a real v1 file made by the previous version opens, then upgrades to v2
# Build a genuine v1 container with the *original* algorithm (PBKDF2 + Fernet) so this
# test does not depend on any old source file being present.
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
_c = sqlite3.connect(":memory:"); _c.executescript(core.SCHEMA)
_c.execute("INSERT INTO text_entries(title,body,tags,created,modified) VALUES ('from v1','old body','legacy',1,1)")
_c.execute("INSERT INTO kv_entries(key,value,created,modified) VALUES ('legacy-key','legacy-val',1,1)")
_c.commit(); _plain = _c.serialize(); _c.close()
_salt = os.urandom(16); _it = 2000
_key = base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_salt, iterations=_it).derive(b"legacy-pw"))
open(P("legacy.vdb"), "wb").write(MAGIC_V1 + _salt + struct.pack(">I", _it) + Fernet(_key).encrypt(_plain))
assert open(P("legacy.vdb"), "rb").read().startswith(MAGIC_V1)
lv = Vault.open(P("legacy.vdb"), "legacy-pw")
assert lv.upgraded_from_v1 and lv.list_texts()[0][1] == "from v1"
try: Vault.open(P("legacy.vdb"), "wrong"); raise SystemExit("FAIL")
except WrongPasswordError: pass
lv.save(); lv.close()
assert open(P("legacy.vdb"), "rb").read().startswith(MAGIC_V2)
lv = Vault.open(P("legacy.vdb"), "legacy-pw")
assert lv.list_kv()[0] == ("legacy-key", "legacy-val", lv.list_kv()[0][2])
ok("v1 file opens, then is upgraded to v2 on save and still opens")

# ---- 13. plain SQLite still works, and unencrypted create/open
p = Vault.create(P("plain.db")); p.add_text("t", "b"); p.save(); p.close()
assert not is_encrypted_container(P("plain.db"))
assert Vault.open(P("plain.db")).stats().texts == 1
ok("plain (unencrypted) database")

# ---- 14. verify_password
v2 = Vault.create(P("vp.vdb"), "abc12345", FAST)
assert v2.verify_password("abc12345") and not v2.verify_password("abc1234") and not v2.verify_password("")
ok("verify_password")

# ---- 15. default scrypt parameters are sane and in the header
dv = Vault.create(P("def.vdb"), "pw-default"); dv.close()
h = open(P("def.vdb"), "rb").read()
assert (h[6], h[7], h[8]) == (17, 8, 1)
ok("default header params N=2^17 r=8 p=1")

print("\nALL CORE TESTS PASSED")
