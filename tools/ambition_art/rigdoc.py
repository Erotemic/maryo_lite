"""Minimal standalone equivalents of Ambition rigdoc drawing primitives."""
from PIL import Image

def downsampled_canvas(frame, size, resample=None):
    return frame.resize(size, resample or Image.Resampling.LANCZOS)
