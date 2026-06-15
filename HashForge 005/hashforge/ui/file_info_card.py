"""
HashForge — FileInfoCard widget.
Displays file name, size, path in a glass-morphism card.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSizePolicy,
)
from PySide6.QtGui import QFontMetrics

from hashforge.core.hasher import FileInfo


class FileInfoCard(QWidget):
    """Compact card showing key file metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileInfoCard")
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(20)

        # File icon
        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 28px; background: transparent;")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Text block
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self._name_label = QLabel("filename.bin")
        self._name_label.setStyleSheet(
            "font-weight: 700; font-size: 14px; color: #0F172A; background: transparent;"
        )

        self._meta_label = QLabel("0 B · /path/to/file")
        self._meta_label.setStyleSheet(
            "font-size: 12px; color: #64748B; background: transparent;"
        )
        self._meta_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        text_layout.addWidget(self._name_label)
        text_layout.addWidget(self._meta_label)

        outer.addWidget(icon)
        outer.addLayout(text_layout)

        self.setStyleSheet("""
            #fileInfoCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EFF6FF, stop:1 #F8FAFC
                );
                border: 1px solid #BFDBFE;
                border-radius: 12px;
            }
        """)

    def update_info(self, file_info: FileInfo):
        self._name_label.setText(file_info.name)
        # Truncate long paths in the middle
        path = file_info.path
        self._meta_label.setText(f"{file_info.size_human}  ·  {path}")
        self._meta_label.setToolTip(path)
        self.setVisible(True)

    def set_dark(self, dark: bool):
        if dark:
            self._name_label.setStyleSheet(
                "font-weight: 700; font-size: 14px; color: #E6EDF3; background: transparent;"
            )
            self._meta_label.setStyleSheet(
                "font-size: 12px; color: #8B949E; background: transparent;"
            )
            self.setStyleSheet("""
                #fileInfoCard {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1E3A5F, stop:1 #161B22
                    );
                    border: 1px solid #1D4ED8;
                    border-radius: 12px;
                }
            """)
        else:
            self._name_label.setStyleSheet(
                "font-weight: 700; font-size: 14px; color: #0F172A; background: transparent;"
            )
            self._meta_label.setStyleSheet(
                "font-size: 12px; color: #64748B; background: transparent;"
            )
            self.setStyleSheet("""
                #fileInfoCard {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #EFF6FF, stop:1 #F8FAFC
                    );
                    border: 1px solid #BFDBFE;
                    border-radius: 12px;
                }
            """)
