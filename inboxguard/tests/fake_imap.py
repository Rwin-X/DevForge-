"""In-memory stand-in for imaplib.IMAP4_SSL, enough for MailboxClient and the engine."""
import imaplib
import re


class FakeIMAP:
    def __init__(self, folders: dict[str, dict[int, bytes]], *, caps=b"IMAP4rev1 UIDPLUS MOVE",
                 password="secret", trash="[Gmail]/Trash", sent="[Gmail]/Sent Mail"):
        self.store = {name: {uid: {"raw": raw, "flags": set()} for uid, raw in msgs.items()}
                      for name, msgs in folders.items()}
        self.caps = caps
        self.password = password
        self.trash, self.sent = trash, sent
        self.selected = None
        self.commands: list[tuple] = []
        self.next_uid = 1000

    def factory(self, host, port):
        return self

    # -- connection ----
    def login(self, user, pw):
        if pw != self.password:
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
        return "OK", [b"logged in"]

    def logout(self):
        return "BYE", [b"bye"]

    def capability(self):
        return "OK", [self.caps]

    def list(self):
        lines = []
        for name in self.store:
            attrs = "\\HasNoChildren"
            if name == self.trash:
                attrs += " \\Trash"
            if name == self.sent:
                attrs += " \\Sent"
            lines.append(f'({attrs}) "/" "{name}"'.encode())
        lines.append(b'(\\Noselect \\HasChildren) "/" "[Gmail]"')
        return "OK", lines

    def select(self, mailbox, readonly=False):
        name = mailbox.strip('"')
        if name not in self.store:
            return "NO", [b"no such folder"]
        self.selected = name
        return "OK", [str(len(self.store[name])).encode()]

    def response(self, code):
        return code, [b"4242"]

    def expunge(self):
        self.commands.append(("EXPUNGE",))
        self._purge(None)
        return "OK", [None]

    # -- UID commands ----
    def uid(self, command, *args):
        command = command.upper()
        self.commands.append((command, *args))
        box = self.store[self.selected]
        if command == "SEARCH":
            crit = [a for a in args if a is not None]
            if crit[:2] == ["HEADER", "Message-ID"]:
                wanted = crit[2].strip('"').encode()
                hits = [u for u, m in box.items() if b"Message-ID: " + wanted in m["raw"]]
            else:
                hits = list(box)
            return "OK", [" ".join(str(u) for u in sorted(hits)).encode()]
        if command == "FETCH":
            return "OK", self._fetch(box, args[0], args[1])
        if command == "MOVE":
            dest = args[1].strip('"')
            for uid in self._uids(args[0]):
                self.store[dest][self.next_uid] = box.pop(uid)
                self.next_uid += 1
            return "OK", [b"moved"]
        if command == "COPY":
            dest = args[1].strip('"')
            for uid in self._uids(args[0]):
                self.store[dest][self.next_uid] = {"raw": box[uid]["raw"], "flags": set(box[uid]["flags"])}
                self.next_uid += 1
            return "OK", [b"copied"]
        if command == "STORE":
            op, flags = args[1], args[2].strip("()")
            for uid in self._uids(args[0]):
                if uid in box:
                    (box[uid]["flags"].add if op.startswith("+") else box[uid]["flags"].discard)(flags)
            return "OK", [None]
        if command == "EXPUNGE":
            self._purge(set(self._uids(args[0])))
            return "OK", [None]
        return "BAD", [b"unknown"]

    # -- helpers ----
    @staticmethod
    def _uids(spec):
        return [int(x) for x in spec.split(",") if x]

    def _purge(self, only):
        box = self.store[self.selected]
        for uid in [u for u, m in box.items() if "\\Deleted" in m["flags"] and (only is None or u in only)]:
            del box[uid]

    def _fetch(self, box, uid_set, spec):
        out = []
        for uid in self._uids(uid_set):
            if uid not in box:
                continue
            msg = box[uid]
            flags = " ".join(sorted(msg["flags"]))
            raw = msg["raw"]
            if "HEADER.FIELDS" in spec:
                raw = raw.split(b"\n\n", 1)[0] + b"\r\n\r\n"
            literal = f"{uid} (UID {uid} FLAGS ({flags}) BODY[] {{{len(raw)}}}".encode()
            out.append((literal, raw))
            out.append(b")")
        return out
