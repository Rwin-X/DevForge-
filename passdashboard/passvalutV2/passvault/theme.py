"""theme.py — Central color palette and font constants for the UI."""


class Palette:
    bg = "#0f1115"
    surface = "#161920"
    surface_alt = "#1c2029"
    border = "#262b36"
    text = "#e8eaed"
    text_dim = "#8b92a3"
    accent = "#6ea8fe"
    accent_dim = "#3d5a8a"
    danger = "#e56b6b"
    danger_dim = "#5a3232"
    success = "#5fbf8a"
    warning = "#e0b355"
    font_family = "Helvetica"

    # Password strength colors, indexed 0 (very weak) .. 4 (very strong)
    strength_colors = ["#e56b6b", "#e0895a", "#e0b355", "#8fbf6a", "#5fbf8a"]
