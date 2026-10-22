"""Small 3D helpers shared by the visualizers."""
import numpy as np


def rotate(pts, yaw, pitch):
    """Rotate points of shape (..., 3) around Y (yaw) and then X (pitch)."""
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    x = pts[..., 0] * cy + pts[..., 2] * sy
    z = -pts[..., 0] * sy + pts[..., 2] * cy
    y = pts[..., 1] * cp - z * sp
    z = pts[..., 1] * sp + z * cp
    return np.stack([x, y, z], -1)


def project(pts, cx, cy, zoom):
    """Perspective projection. Returns (screen_xy, depth)."""
    f = zoom * 900.0 / (1400.0 + pts[..., 2])
    return np.stack([cx + pts[..., 0] * f, cy + pts[..., 1] * f], -1), pts[..., 2]
