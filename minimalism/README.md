# Pulse (Python)

Audio-reactive 3D music visualizers sharing one engine.

    pip install -r requirements.txt
    python run_pygame.py [audio_file]     # wireframe sphere + rhythm-bound core
    python run_qt.py [audio_file]         # PyQt6 desktop player with a torus
    python run_terminal.py [audio_file]   # spectrum bars in the terminal

With no file, a synthesized demo track plays. Supported formats depend on libsndfile (WAV, FLAC, OGG, MP3).

Layout: core/ holds audio playback, analysis and 3D math (no GUI imports); ui/ holds the Qt layer.
pygame keys: SPACE play/pause, LEFT/RIGHT seek, UP/DOWN volume, O open, T theme, ESC quit.
