from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from ...core.mailbox import FolderInfo
from ...core.service import Listing, MessageDetail
from ..backend import Backend
from ..widgets.common import (
    NoticeLabel, category_phrase, fmt_when, make_header, make_table, selected_rows, text_item,
)
from .. import style


class MailboxPage(QWidget):
    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        self._folders: list[FolderInfo] = []
        self._listing: Listing | None = None
        self._stale = True
        self._list_token = 0
        self._preview_token = 0
        self._build()
        backend.scan_finished.connect(self.mark_stale)
        backend.config_changed.connect(self._on_config_changed)

    # ---- layout --------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(10)
        layout.addWidget(make_header("Mailbox", "Browse, read and manage your messages"))

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.folder_box = QComboBox()
        self.folder_box.setMinimumWidth(190)
        self.folder_box.currentIndexChanged.connect(self._on_folder_changed)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.reload)
        self.limit_box = QSpinBox()
        self.limit_box.setRange(25, 1000)
        self.limit_box.setSingleStep(25)
        self.limit_box.setValue(100)
        self.limit_box.setPrefix("Last ")
        self.limit_box.setMinimumWidth(110)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by sender or subject")
        self.filter_edit.textChanged.connect(self._apply_filter)
        self.unread_check = QCheckBox("Unread only")
        self.unread_check.toggled.connect(self._apply_filter)
        for widget in (self.folder_box, self.refresh_btn, self.limit_box):
            bar.addWidget(widget)
        bar.addWidget(self.filter_edit, 1)
        bar.addWidget(self.unread_check)
        layout.addLayout(bar)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.trash_btn = QPushButton("Move to Trash")
        self.trash_btn.setObjectName("destructiveAction")
        self.trash_btn.clicked.connect(self._trash_clicked)
        self.read_btn = QPushButton("Mark read")
        self.read_btn.clicked.connect(lambda: self._set_seen(True))
        self.unread_btn = QPushButton("Mark unread")
        self.unread_btn.clicked.connect(lambda: self._set_seen(False))
        self.move_btn = QPushButton("Move to")
        self.move_menu = QMenu(self.move_btn)
        self.move_btn.setMenu(self.move_menu)
        self.trust_btn = QPushButton("Trust sender")
        self.trust_btn.clicked.connect(self._trust_clicked)
        self.block_btn = QPushButton("Block sender")
        self.block_btn.clicked.connect(self._block_clicked)
        for button in (self.trash_btn, self.read_btn, self.unread_btn, self.move_btn, self.trust_btn, self.block_btn):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)

        self.notice = NoticeLabel()
        layout.addWidget(self.notice)

        split = QSplitter(Qt.Orientation.Vertical)
        self.table = make_table(["Date", "From", "Subject", "Scan result"], [145, 250, 0, 220], stretch=2)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a message to preview it. Messages are shown as plain text only; "
                                        "remote images and scripts are never loaded.")
        split.addWidget(self.table)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)
        self._update_buttons()

    # ---- page lifecycle -----------------------------------------------

    def on_activated(self) -> None:
        if not self._configured():
            self.notice.info("Configure your account in Settings first.")
            return
        if not self._folders:
            self._load_folders()
        elif self._stale:
            self.reload()

    def mark_stale(self, *_args) -> None:
        self._stale = True

    def _configured(self) -> bool:
        acc = self.backend.ctx.config.account
        return bool(acc.username and acc.host)

    def _on_config_changed(self) -> None:
        self._folders = []
        self._listing = None
        self.folder_box.blockSignals(True)
        self.folder_box.clear()
        self.folder_box.blockSignals(False)
        self.table.setRowCount(0)
        self.preview.clear()
        self._stale = True

    # ---- folders -------------------------------------------------------

    def _load_folders(self) -> None:
        self.notice.info("Loading folders")
        self.backend.run(self.backend.service.folders, self._on_folders, self._on_error)

    def _on_folders(self, folders: list[FolderInfo]) -> None:
        self._folders = folders
        wanted = self.backend.ctx.config.bot.scan_folder
        self.folder_box.blockSignals(True)
        self.folder_box.clear()
        for folder in folders:
            self.folder_box.addItem(folder.display, folder.name)
        index = max(0, self.folder_box.findData(wanted))
        self.folder_box.setCurrentIndex(index)
        self.folder_box.blockSignals(False)
        self._rebuild_move_menu()
        self.reload()

    def _current_folder(self) -> str:
        return self.folder_box.currentData() or ""

    def _folder_info(self) -> FolderInfo | None:
        name = self._current_folder()
        return next((f for f in self._folders if f.name == name), None)

    def _in_trash(self) -> bool:
        info = self._folder_info()
        return bool(info and info.has_attr("\\Trash"))

    def _on_folder_changed(self, _index: int) -> None:
        self._rebuild_move_menu()
        self.reload()

    def _rebuild_move_menu(self) -> None:
        self.move_menu.clear()
        current = self._current_folder()
        for folder in self._folders:
            if folder.name == current:
                continue
            action = self.move_menu.addAction(folder.display)
            action.triggered.connect(lambda _checked=False, name=folder.name: self._move_to(name))
        self.trash_btn.setText("Delete permanently" if self._in_trash() else "Move to Trash")

    # ---- listing -------------------------------------------------------

    def reload(self) -> None:
        folder = self._current_folder()
        if not folder:
            return
        self._stale = False
        self._list_token += 1
        token = self._list_token
        limit = self.limit_box.value()
        self.notice.info("Loading messages")
        self.backend.run(
            lambda: self.backend.service.list_messages(folder, limit),
            lambda listing: self._on_listing(token, listing),
            self._on_error,
        )

    def _on_listing(self, token: int, listing: Listing) -> None:
        if token != self._list_token:
            return
        self.notice.clear_notice()
        self._listing = listing
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        for index, row in enumerate(listing.rows):
            mail = row.mail
            r = self.table.rowCount()
            self.table.insertRow(r)
            unread = mail.is_unread
            result = ""
            if row.status:
                result = row.status.capitalize()
                if row.category:
                    result += f" ({category_phrase(row.category)} {row.score:.2f})"
            color = style.ACCENT if row.status == "trashed" else None
            self.table.setItem(r, 0, text_item(fmt_when(mail.date), index, bold=unread))
            self.table.setItem(r, 1, text_item(mail.sender_display, bold=unread))
            self.table.setItem(r, 2, text_item(mail.subject or "(no subject)", bold=unread))
            self.table.setItem(r, 3, text_item(result, color=color))
        self.table.setUpdatesEnabled(True)
        self._apply_filter()
        self.preview.clear()
        self._update_buttons()

    def _apply_filter(self, *_args) -> None:
        if self._listing is None:
            return
        needle = self.filter_edit.text().strip().lower()
        unread_only = self.unread_check.isChecked()
        for r in range(self.table.rowCount()):
            mail = self._listing.rows[self.table.item(r, 0).data(Qt.ItemDataRole.UserRole)].mail
            hay = f"{mail.sender_display} {mail.subject}".lower()
            hidden = (bool(needle) and needle not in hay) or (unread_only and not mail.is_unread)
            self.table.setRowHidden(r, hidden)

    # ---- selection and preview ------------------------------------------

    def _selected_mails(self):
        if self._listing is None:
            return []
        rows = selected_rows(self.table)
        return [self._listing.rows[self.table.item(r, 0).data(Qt.ItemDataRole.UserRole)].mail for r in rows]

    def _update_buttons(self) -> None:
        has = bool(self._selected_mails())
        for button in (self.trash_btn, self.read_btn, self.unread_btn, self.move_btn, self.trust_btn, self.block_btn):
            button.setEnabled(has)

    def _on_selection(self) -> None:
        self._update_buttons()
        mails = self._selected_mails()
        self._preview_token += 1
        if len(mails) != 1:
            self.preview.setPlainText(f"{len(mails)} messages selected." if mails else "")
            return
        token = self._preview_token
        folder, uid = self._current_folder(), mails[0].uid
        self.preview.setPlainText("Loading message")
        self.backend.run(
            lambda: self.backend.service.load_message(folder, uid),
            lambda detail: self._show_detail(token, detail),
            lambda msg: self._show_preview_error(token, msg),
        )

    def _show_preview_error(self, token: int, message: str) -> None:
        if token == self._preview_token:
            self.preview.setPlainText(message)

    def _show_detail(self, token: int, detail: MessageDetail) -> None:
        if token != self._preview_token:
            return
        mail, result = detail.mail, detail.result
        lines = [
            f"From:    {mail.sender_display}",
            f"To:      {mail.recipients}",
            f"Date:    {fmt_when(mail.date)}",
            f"Subject: {mail.subject}",
            "",
            f"Advertisement score: {result.ad_score:.2f}    AI-written score: {result.ai_score:.2f}",
        ]
        for reason in result.ad_reasons + result.ai_reasons:
            lines.append(f"  - {reason}")
        lines += ["", "-" * 60, "", mail.text or "(no text content)"]
        self.preview.setPlainText("\n".join(lines))

    # ---- actions -------------------------------------------------------

    def _on_error(self, message: str) -> None:
        self.notice.error(message)

    def _after(self, message: str) -> None:
        self.notice.ok(message)
        self.backend.status.emit(message)
        self.backend.data_changed.emit()
        self.reload()

    def _trash_clicked(self) -> None:
        mails = self._selected_mails()
        folder = self._current_folder()
        if not mails:
            return
        if self._in_trash():
            answer = QMessageBox.warning(
                self, "Delete permanently",
                f"Permanently delete {len(mails)} message(s)? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.backend.run(
                lambda: self.backend.service.delete_permanently(folder, mails),
                lambda n: self._after(f"Permanently deleted {n} message(s)"), self._on_error,
            )
            return
        self.backend.run(
            lambda: self.backend.service.trash_messages(folder, mails),
            lambda n: self._after(f"Moved {n} message(s) to Trash"), self._on_error,
        )

    def _set_seen(self, seen: bool) -> None:
        mails, folder = self._selected_mails(), self._current_folder()
        self.backend.run(
            lambda: self.backend.service.set_seen(folder, mails, seen),
            lambda n: self._after(f"Marked {n} message(s) as {'read' if seen else 'unread'}"), self._on_error,
        )

    def _move_to(self, dest: str) -> None:
        mails, folder = self._selected_mails(), self._current_folder()
        self.backend.run(
            lambda: self.backend.service.move_messages(folder, mails, dest),
            lambda n: self._after(f"Moved {n} message(s)"), self._on_error,
        )

    def _trust_clicked(self) -> None:
        mails = self._selected_mails()
        self.backend.run(
            lambda: self.backend.service.trust_sender(mails),
            lambda n: (self.notice.ok(f"{n} sender(s) added to the allowlist"), self.backend.config_changed.emit()),
            self._on_error,
        )

    def _block_clicked(self) -> None:
        mails, folder = self._selected_mails(), self._current_folder()
        senders = ", ".join(sorted({m.sender_address for m in mails}))
        answer = QMessageBox.question(
            self, "Block sender",
            f"Block {senders}?\nTheir messages are trashed now and on every future scan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.backend.run(
            lambda: self.backend.service.block_sender(folder, mails),
            lambda n: self._after(f"Blocked sender and trashed {n} message(s)"), self._on_error,
        )
