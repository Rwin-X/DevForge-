"""
Sonar — Find similar music
A minimal PyQt6 desktop app that takes a song you like and finds similar
tracks using the public iTunes Search API. No API key required.

Design language: white canvas, single green accent, generous whitespace —
matching the web version of Sonar.
"""

import sys
import random
from dataclasses import dataclass
from typing import Optional

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QPixmap, QFont, QIcon, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)


# ---------------------------------------------------------------------------
# Palette (mirrors the web version)
# ---------------------------------------------------------------------------
PAPER = "#ffffff"
PAPER_SOFT = "#f5faf7"
INK = "#0d1f16"
INK_SOFT = "#5b6b62"
GREEN = "#1c7a4d"
GREEN_DEEP = "#0f5c39"
GREEN_GLOW = "#2fbf7f"
LINE = "#d9ece2"
GENRE_BG = "#e6f5ec"

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Track:
    track_id: Optional[int]
    title: str
    artist: str
    artist_id: Optional[int]
    genre: str
    artwork_url: str
    preview_url: Optional[str]

    @staticmethod
    def from_api(raw: dict) -> "Track":
        artwork = raw.get("artworkUrl100", "") or ""
        artwork = artwork.replace("100x100bb", "300x300bb")
        return Track(
            track_id=raw.get("trackId"),
            title=raw.get("trackName") or "Unknown title",
            artist=raw.get("artistName") or "Unknown artist",
            artist_id=raw.get("artistId"),
            genre=raw.get("primaryGenreName") or "—",
            artwork_url=artwork,
            preview_url=raw.get("previewUrl"),
        )


# ---------------------------------------------------------------------------
# Background worker: does all networking off the UI thread
# ---------------------------------------------------------------------------
class SimilarTracksWorker(QThread):
    seed_found = pyqtSignal(object)          # Track
    results_ready = pyqtSignal(list)         # list[Track]
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            self.status_update.emit("Looking up the track…")
            seed_raw = self._search(self.query, limit=5)

            if not seed_raw:
                self.error.emit(
                    "Could not find that song. Try a different spelling, "
                    "or include the artist name."
                )
                return

            seed_track = Track.from_api(seed_raw[0])
            self.seed_found.emit(seed_track)

            self.status_update.emit("Finding tracks that sound like this…")

            artist_tracks = []
            if seed_track.artist_id:
                artist_raw = self._lookup_artist(seed_track.artist_id, limit=15)
                artist_tracks = [
                    Track.from_api(r) for r in artist_raw
                    if r.get("wrapperType") == "track"
                ]

            genre_tracks = []
            if seed_track.genre and seed_track.genre != "—":
                genre_raw = self._search(seed_track.genre, limit=40)
                genre_tracks = [
                    Track.from_api(r) for r in genre_raw
                    if r.get("artistName") != seed_track.artist
                ]
                random.shuffle(genre_tracks)

            combined = artist_tracks[:6] + genre_tracks[:14]

            # De-duplicate by (title, artist), excluding the seed itself
            seen = set()
            final = []
            for t in combined:
                if t.track_id == seed_track.track_id:
                    continue
                key = (t.title, t.artist)
                if key in seen:
                    continue
                seen.add(key)
                final.append(t)

            self.results_ready.emit(final)

        except requests.RequestException:
            self.error.emit(
                "Something went wrong reaching the music database. "
                "Please check your connection and try again."
            )
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")

    @staticmethod
    def _search(term: str, limit: int = 25) -> list:
        params = {
            "term": term,
            "media": "music",
            "entity": "song",
            "limit": limit,
        }
        resp = requests.get(ITUNES_SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])

    @staticmethod
    def _lookup_artist(artist_id: int, limit: int = 30) -> list:
        params = {
            "id": artist_id,
            "entity": "song",
            "limit": limit,
        }
        resp = requests.get(ITUNES_LOOKUP_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])


class ArtworkFetcher(QThread):
    """Fetches a single artwork image without blocking the UI."""
    loaded = pyqtSignal(QPixmap)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=8)
            resp.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(resp.content)
            self.loaded.emit(pixmap)
        except Exception:  # noqa: BLE001
            self.loaded.emit(QPixmap())


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def rounded_pixmap(pixmap: QPixmap, size: int, radius: int) -> QPixmap:
    """Scales a pixmap to a square and clips it to rounded corners."""
    if pixmap.isNull():
        result = QPixmap(size, size)
        result.fill(QColor(PAPER_SOFT))
        return result

    scaled = pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path_rect = result.rect()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    painter.drawPixmap(-x, -y, scaled)
    painter.end()
    return result


class PulseBar(QWidget):
    """Small animated waveform logo, mirroring the web version's signature element."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(34, 26)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        heights = [0.4, 1.0, 0.65, 0.85, 0.5]
        bar_w = 4
        gap = 3
        total_w = len(heights) * bar_w + (len(heights) - 1) * gap
        x = (self.width() - total_w) / 2
        painter.setBrush(QColor(GREEN))
        painter.setPen(Qt.PenStyle.NoPen)
        for h in heights:
            bar_h = self.height() * h
            y = self.height() - bar_h
            painter.drawRoundedRect(int(x), int(y), bar_w, int(bar_h), 2, 2)
            x += bar_w + gap


class TrackRow(QFrame):
    """A single result row: artwork, title/artist, genre tag, play button."""

    def __init__(self, track: Track, player_controller: "PreviewPlayer"):
        super().__init__()
        self.track = track
        self.player_controller = player_controller
        self.is_playing = False

        self.setObjectName("trackRow")
        self.setStyleSheet(f"""
            QFrame#trackRow {{
                background: transparent;
                border-radius: 12px;
            }}
            QFrame#trackRow:hover {{
                background: {PAPER_SOFT};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # Artwork
        self.art_label = QLabel()
        self.art_label.setFixedSize(52, 52)
        self.art_label.setPixmap(rounded_pixmap(QPixmap(), 52, 8))
        layout.addWidget(self.art_label)

        if track.artwork_url:
            self.art_fetcher = ArtworkFetcher(track.artwork_url)
            self.art_fetcher.loaded.connect(self._on_artwork_loaded)
            self.art_fetcher.start()

        # Title / artist
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        title_label = QLabel(track.title)
        title_label.setStyleSheet(f"color: {INK}; font-size: 14px; font-weight: 600;")
        title_label.setWordWrap(False)
        artist_label = QLabel(track.artist)
        artist_label.setStyleSheet(f"color: {INK_SOFT}; font-size: 12.5px;")
        info_layout.addWidget(title_label)
        info_layout.addWidget(artist_label)
        info_container = QWidget()
        info_container.setLayout(info_layout)
        layout.addWidget(info_container, stretch=1)

        # Genre tag
        genre_label = QLabel(track.genre)
        genre_label.setStyleSheet(f"""
            color: {GREEN_DEEP};
            background: {GENRE_BG};
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 100px;
        """)
        layout.addWidget(genre_label)

        # Play button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_play_button(playing=False)
        if not track.preview_url:
            self.play_btn.setEnabled(False)
            self.play_btn.setToolTip("No preview available")
        else:
            self.play_btn.setToolTip("Play 30s preview")
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)

    def _on_artwork_loaded(self, pixmap: QPixmap):
        self.art_label.setPixmap(rounded_pixmap(pixmap, 52, 8))

    def _style_play_button(self, playing: bool):
        if playing:
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {GREEN};
                    color: white;
                    border: 1.5px solid {GREEN};
                    border-radius: 18px;
                    font-size: 12px;
                }}
            """)
        else:
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PAPER};
                    color: {GREEN};
                    border: 1.5px solid {LINE};
                    border-radius: 18px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {GREEN};
                    color: white;
                    border-color: {GREEN};
                }}
                QPushButton:disabled {{
                    color: #b7c6bd;
                    border-color: {LINE};
                }}
            """)

    def _toggle_play(self):
        if not self.track.preview_url:
            return
        now_playing = self.player_controller.toggle(self.track.preview_url, self)
        self.set_playing_state(now_playing)

    def set_playing_state(self, playing: bool):
        self.is_playing = playing
        self.play_btn.setText("⏸" if playing else "▶")
        self._style_play_button(playing)


class PreviewPlayer:
    """Owns a single QMediaPlayer and coordinates play/pause across TrackRows."""

    def __init__(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)
        self.current_row: Optional[TrackRow] = None
        self.player.mediaStatusChanged.connect(self._on_status_changed)

    def toggle(self, url: str, row: TrackRow) -> bool:
        """Returns True if this row is now playing, False if paused/stopped."""
        if self.current_row is row:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                return False
            else:
                self.player.play()
                return True

        # Switch to a new track
        if self.current_row is not None:
            self.current_row.set_playing_state(False)

        self.current_row = row
        self.player.setSource(QUrl(url))
        self.player.play()
        return True

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.current_row is not None:
                self.current_row.set_playing_state(False)
            self.current_row = None


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class SonarWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sonar — Find similar music")
        self.resize(640, 760)
        self.setStyleSheet(f"background: {PAPER};")

        self.player_controller = PreviewPlayer()
        self.worker: Optional[SimilarTracksWorker] = None
        self.seed_art_fetcher: Optional[ArtworkFetcher] = None

        self._build_ui()

    # -- UI construction ----------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 48, 40, 32)
        outer.setSpacing(0)

        # Brand row
        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        brand_row.addStretch()
        brand_row.addWidget(PulseBar())
        wordmark = QLabel('Son<span style="color:%s;">ar</span>' % GREEN)
        wordmark.setTextFormat(Qt.TextFormat.RichText)
        wordmark.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {INK};")
        brand_row.addWidget(wordmark)
        brand_row.addStretch()
        outer.addLayout(brand_row)

        tagline = QLabel(
            "Type a song you love. Sonar listens for its shape — artist, genre, era —\n"
            "and finds tracks that echo it."
        )
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(f"color: {INK_SOFT}; font-size: 13.5px; margin-top: 8px;")
        outer.addWidget(tagline)
        outer.addSpacing(28)

        # Search box
        search_frame = QFrame()
        search_frame.setObjectName("searchFrame")
        search_frame.setStyleSheet(f"""
            QFrame#searchFrame {{
                background: {PAPER};
                border: 1.5px solid {LINE};
                border-radius: 14px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(18, 6, 6, 6)
        search_layout.setSpacing(10)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Song title, or artist — song")
        self.query_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-size: 15px;
                color: {INK};
                padding: 12px 0;
            }}
        """)
        self.query_input.returnPressed.connect(self._on_search_clicked)
        search_layout.addWidget(self.query_input, stretch=1)

        self.search_btn = QPushButton("Find similar")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {GREEN};
                color: white;
                font-weight: 600;
                font-size: 13.5px;
                padding: 12px 20px;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{ background: {GREEN_DEEP}; }}
            QPushButton:disabled {{ background: #a9c9b8; }}
        """)
        self.search_btn.clicked.connect(self._on_search_clicked)
        search_layout.addWidget(self.search_btn)

        outer.addWidget(search_frame)

        hint = QLabel('Try "Redbone" or "Tame Impala — The Less I Know The Better"')
        hint.setStyleSheet(f"color: {INK_SOFT}; font-size: 11.5px; margin-top: 8px; padding-left: 4px;")
        outer.addWidget(hint)

        outer.addSpacing(24)

        # Status label (loading / error)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {INK_SOFT}; font-size: 13.5px;")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        outer.addWidget(self.status_label)

        # Seed track card
        self.seed_card = QFrame()
        self.seed_card.setVisible(False)
        self.seed_card.setStyleSheet(f"""
            QFrame {{
                background: {PAPER_SOFT};
                border: 1px solid {LINE};
                border-radius: 14px;
            }}
        """)
        seed_layout = QHBoxLayout(self.seed_card)
        seed_layout.setContentsMargins(14, 14, 14, 14)
        seed_layout.setSpacing(16)

        self.seed_art_label = QLabel()
        self.seed_art_label.setFixedSize(56, 56)
        seed_layout.addWidget(self.seed_art_label)

        seed_info_layout = QVBoxLayout()
        seed_info_layout.setSpacing(2)
        self.seed_title_label = QLabel()
        self.seed_title_label.setStyleSheet(f"color: {INK}; font-size: 15px; font-weight: 650;")
        self.seed_meta_label = QLabel()
        self.seed_meta_label.setStyleSheet(f"color: {INK_SOFT}; font-size: 13px;")
        seed_info_layout.addWidget(self.seed_title_label)
        seed_info_layout.addWidget(self.seed_meta_label)
        seed_info_container = QWidget()
        seed_info_container.setLayout(seed_info_layout)
        seed_layout.addWidget(seed_info_container, stretch=1)

        seed_wrap = QVBoxLayout()
        seed_label = QLabel("YOU PICKED")
        seed_label.setStyleSheet(f"""
            color: {GREEN};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        seed_wrap.addWidget(seed_label)
        seed_wrap.addSpacing(8)
        seed_wrap.addWidget(self.seed_card)
        outer.addLayout(seed_wrap)
        self.seed_label_widget = seed_label
        seed_label.setVisible(False)

        outer.addSpacing(20)

        results_label = QLabel("SIMILAR TRACKS")
        results_label.setStyleSheet(f"""
            color: {INK_SOFT};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        results_label.setVisible(False)
        self.results_label_widget = results_label
        outer.addWidget(results_label)
        outer.addSpacing(10)

        # Scrollable results area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        self.results_container = QWidget()
        self.results_container.setStyleSheet("background: transparent;")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(2)
        self.results_layout.addStretch()

        self.scroll_area.setWidget(self.results_container)
        outer.addWidget(self.scroll_area, stretch=1)

        footer = QLabel("Powered by the iTunes Search API · previews are 30-second clips")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: #a9b9af; font-size: 11px; margin-top: 12px;")
        outer.addWidget(footer)

    # -- Search flow ----------------------------------------------------
    def _on_search_clicked(self):
        query = self.query_input.text().strip()
        if not query:
            self.query_input.setFocus()
            return

        self._clear_results()
        self.seed_card.setVisible(False)
        self.seed_label_widget.setVisible(False)
        self.results_label_widget.setVisible(False)
        self.status_label.setVisible(True)
        self.status_label.setText("Searching…")
        self.search_btn.setEnabled(False)

        self.worker = SimilarTracksWorker(query)
        self.worker.seed_found.connect(self._on_seed_found)
        self.worker.results_ready.connect(self._on_results_ready)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.worker.start()

    def _on_status_update(self, text: str):
        self.status_label.setText(text)

    def _on_seed_found(self, track: Track):
        self.seed_title_label.setText(track.title)
        meta = track.artist
        if track.genre and track.genre != "—":
            meta += f" · {track.genre}"
        self.seed_meta_label.setText(meta)
        self.seed_art_label.setPixmap(rounded_pixmap(QPixmap(), 56, 8))

        if track.artwork_url:
            self.seed_art_fetcher = ArtworkFetcher(track.artwork_url)
            self.seed_art_fetcher.loaded.connect(
                lambda pm: self.seed_art_label.setPixmap(rounded_pixmap(pm, 56, 8))
            )
            self.seed_art_fetcher.start()

        self.seed_card.setVisible(True)
        self.seed_label_widget.setVisible(True)

    def _on_results_ready(self, tracks: list):
        self.status_label.setVisible(False)

        if not tracks:
            self.status_label.setVisible(True)
            self.status_label.setText("No similar tracks found. Try a different song.")
            return

        self.results_label_widget.setVisible(True)
        self._clear_results()

        for i, track in enumerate(tracks):
            row = TrackRow(track, self.player_controller)
            self.results_layout.insertWidget(self.results_layout.count() - 1, row)
            if i < len(tracks) - 1:
                divider = QFrame()
                divider.setFixedHeight(1)
                divider.setStyleSheet(f"background: {LINE};")
                self.results_layout.insertWidget(self.results_layout.count() - 1, divider)

    def _on_error(self, message: str):
        self.status_label.setVisible(True)
        self.status_label.setText(message)

    def _clear_results(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = SonarWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
