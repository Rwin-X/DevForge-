from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from ...core.config import PROVIDERS, AppConfig
from ...core.service import check_connection
from ..backend import Backend
from ..widgets.common import NoticeLabel, make_header


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("tertiaryLabel")
    label.setWordWrap(True)
    return label


def _threshold_box(value: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0.10, 1.00)
    box.setSingleStep(0.05)
    box.setDecimals(2)
    box.setValue(value)
    return box


class SettingsPage(QWidget):
    def __init__(self, backend: Backend):
        super().__init__()
        self.backend = backend
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(10)
        outer.addWidget(make_header("Settings", "Account, bot behaviour and deletion rules"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(0, 0, 12, 0)
        form.setSpacing(14)
        form.addWidget(self._account_group())
        form.addWidget(self._bot_group())
        form.addWidget(self._policy_group())
        form.addWidget(self._lists_group())
        form.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        bar = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("primaryAction")
        self.save_btn.clicked.connect(self._save)
        self.notice = NoticeLabel()
        self.save_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        bar.addWidget(self.save_btn)
        bar.addWidget(self.notice, 1)
        bar.addStretch()
        outer.addLayout(bar)

        for spin in (self.port, self.scan_days, self.max_per_scan, self.interval,
                     self.ad_trash, self.ad_review, self.ai_trash, self.ai_review):
            spin.setMaximumWidth(160)
        self.load_from_config()
        backend.config_changed.connect(self.load_from_config)

    # ---- groups --------------------------------------------------------

    def _account_group(self) -> QGroupBox:
        group = QGroupBox("Account (IMAP)")
        form = QFormLayout(group)
        form.setSpacing(10)
        self.provider = QComboBox()
        self.provider.addItems(list(PROVIDERS))
        self.provider.currentTextChanged.connect(self._on_provider)
        self.host = QLineEdit()
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.username = QLineEdit()
        self.username.setPlaceholderText("you@example.com")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Stored in the system keyring. Leave empty to keep the saved one.")
        form.addRow("Provider", self.provider)
        form.addRow("Server", self.host)
        form.addRow("Port (TLS)", self.port)
        form.addRow("Username", self.username)
        form.addRow("App password", self.password)
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self._test)
        self.test_notice = NoticeLabel()
        self.test_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_notice, 1)
        test_row.addStretch()
        form.addRow("", test_row)
        form.addRow("", _note(
            "Gmail, Yahoo, iCloud and Fastmail require an app password (2-step verification must be on). "
            "Microsoft Outlook and 365 accounts need OAuth2, which this version does not support."
        ))
        return group

    def _bot_group(self) -> QGroupBox:
        group = QGroupBox("Bot")
        form = QFormLayout(group)
        form.setSpacing(10)
        self.scan_folder = QLineEdit()
        self.scan_days = QSpinBox()
        self.scan_days.setRange(1, 365)
        self.scan_days.setSuffix(" days")
        self.max_per_scan = QSpinBox()
        self.max_per_scan.setRange(10, 2000)
        self.max_per_scan.setSingleStep(10)
        self.interval = QSpinBox()
        self.interval.setRange(1, 1440)
        self.interval.setSuffix(" min")
        self.auto_scan = QCheckBox("Start the bot automatically when the app opens")
        form.addRow("Folder to scan", self.scan_folder)
        form.addRow("Look back", self.scan_days)
        form.addRow("Max messages per scan", self.max_per_scan)
        form.addRow("Scan every", self.interval)
        form.addRow("", self.auto_scan)
        return group

    def _policy_group(self) -> QGroupBox:
        group = QGroupBox("Deletion rules")
        form = QFormLayout(group)
        form.setSpacing(10)
        self.dry_run = QCheckBox("Dry run: never trash, send every match to Review")
        self.protect = QCheckBox("Never touch senders I have written to before (reads the Sent folder)")
        self.ad_trash = _threshold_box(0.80)
        self.ad_review = _threshold_box(0.55)
        self.ai_trash = _threshold_box(0.90)
        self.ai_review = _threshold_box(0.60)
        form.addRow("", self.dry_run)
        form.addRow("", self.protect)
        form.addRow("Advertisement: trash at", self.ad_trash)
        form.addRow("Advertisement: review at", self.ad_review)
        form.addRow("AI-written: trash at", self.ai_trash)
        form.addRow("AI-written: review at", self.ai_review)
        form.addRow("", _note(
            "Scores run from 0 to 1. Advertisement detection uses structural evidence (unsubscribe headers, "
            "bulk-mail platforms, tracking pixels) and is reliable. AI-written detection is heuristic: no "
            "tool can prove who wrote a text, and formal human writing can score high. Keep the AI trash "
            "threshold high. At 0.90 only pasted assistant boilerplate and template placeholders are trashed."
        ))
        return group

    def _lists_group(self) -> QGroupBox:
        group = QGroupBox("Sender lists")
        form = QFormLayout(group)
        form.setSpacing(10)
        self.allowlist = QPlainTextEdit()
        self.allowlist.setFixedHeight(90)
        self.blocklist = QPlainTextEdit()
        self.blocklist.setFixedHeight(90)
        form.addRow("Always keep", self.allowlist)
        form.addRow("Always trash", self.blocklist)
        form.addRow("", _note("One entry per line: a full address (a@b.com) or a domain (b.com, includes subdomains)."))
        return group

    # ---- config <-> widgets --------------------------------------------

    def _on_provider(self, name: str) -> None:
        host, port = PROVIDERS.get(name, ("", 993))
        if name != "Custom":
            self.host.setText(host)
            self.port.setValue(port)
        self.host.setReadOnly(name != "Custom")

    def load_from_config(self) -> None:
        cfg = self.backend.ctx.config
        acc, bot, pol = cfg.account, cfg.bot, cfg.policy
        self.provider.blockSignals(True)
        self.provider.setCurrentText(acc.provider if acc.provider in PROVIDERS else "Custom")
        self.provider.blockSignals(False)
        self.host.setText(acc.host)
        self.host.setReadOnly(self.provider.currentText() != "Custom")
        self.port.setValue(acc.port)
        self.username.setText(acc.username)
        self.password.clear()
        self.scan_folder.setText(bot.scan_folder)
        self.scan_days.setValue(bot.scan_days)
        self.max_per_scan.setValue(bot.max_messages_per_scan)
        self.interval.setValue(bot.interval_minutes)
        self.auto_scan.setChecked(bot.auto_scan)
        self.dry_run.setChecked(pol.dry_run)
        self.protect.setChecked(pol.protect_correspondents)
        self.ad_trash.setValue(pol.ad_trash_threshold)
        self.ad_review.setValue(pol.ad_review_threshold)
        self.ai_trash.setValue(pol.ai_trash_threshold)
        self.ai_review.setValue(pol.ai_review_threshold)
        self.allowlist.setPlainText("\n".join(pol.allowlist))
        self.blocklist.setPlainText("\n".join(pol.blocklist))

    def _collect(self) -> AppConfig:
        cfg = deepcopy(self.backend.ctx.config)
        cfg.account.provider = self.provider.currentText()
        cfg.account.host = self.host.text()
        cfg.account.port = self.port.value()
        cfg.account.username = self.username.text()
        cfg.bot.scan_folder = self.scan_folder.text()
        cfg.bot.scan_days = self.scan_days.value()
        cfg.bot.max_messages_per_scan = self.max_per_scan.value()
        cfg.bot.interval_minutes = self.interval.value()
        cfg.bot.auto_scan = self.auto_scan.isChecked()
        cfg.policy.dry_run = self.dry_run.isChecked()
        cfg.policy.protect_correspondents = self.protect.isChecked()
        cfg.policy.ad_trash_threshold = self.ad_trash.value()
        cfg.policy.ad_review_threshold = self.ad_review.value()
        cfg.policy.ai_trash_threshold = self.ai_trash.value()
        cfg.policy.ai_review_threshold = self.ai_review.value()
        cfg.policy.allowlist = self.allowlist.toPlainText().splitlines()
        cfg.policy.blocklist = self.blocklist.toPlainText().splitlines()
        return cfg

    def _save(self) -> None:
        password = self.password.text() or None
        self.backend.apply_config(self._collect(), password)
        self.notice.ok("Settings saved")

    def _test(self) -> None:
        host, port = self.host.text().strip(), self.port.value()
        user, typed = self.username.text().strip(), self.password.text()
        ctx = self.backend.ctx
        self.test_notice.info("Connecting")

        def work() -> str:
            password = typed or ctx.password_provider(user)
            return check_connection(ctx.client_factory, host, port, user, password)

        self.backend.run(work, self.test_notice.ok, self.test_notice.error)
