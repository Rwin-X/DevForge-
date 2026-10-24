# Pulse (Python)

Audio-reactive 3D music visualizers sharing one engine.

    pip install -r requirements.txt
    python run_pygame.py [audio_file]     # wireframe sphere + rhythm-bound core
    python run_styles.py [audio_file]     # nine 3D styles, TAB or 1-9 to switch
    python run_qt.py [audio_file]         # PyQt6 desktop player, STYLE button cycles the nine styles
    python run_terminal.py [audio_file]   # spectrum bars in the terminal

With no file, a synthesized demo track plays. Supported formats depend on libsndfile (WAV, FLAC, OGG, MP3).

Layout: core/ holds audio playback, analysis, 3D math and scene geometry (no GUI imports); ui/ holds the Qt layer.
Styles (core/scenes.py): Torus, Helix, Terrain, Tunnel, Lattice, Galaxy, Ripple, Bars, Strings.
A scene returns line segments, points and polylines; each renderer (pygame, Qt) only draws them, so a new style works in both.
pygame keys: SPACE play/pause, LEFT/RIGHT seek, UP/DOWN volume, O open, T theme, ESC quit.
