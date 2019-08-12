# generic6502 input template locations
import numpy as np

VIDEO_WIDTH = 40
VIDEO_HEIGHT = 192

VIDEO_SIZE = VIDEO_WIDTH * VIDEO_HEIGHT
AUDIO_SIZE = 2048
MAIN_MEMORY_SIZE = 1<<16
STATESAV_MAX_SIZE = 256 + MAIN_MEMORY_SIZE + 256


OUTPUT_DTYPE = np.dtype([
    ("state", np.uint8, STATESAV_MAX_SIZE),
    ("video", np.uint8, VIDEO_SIZE),
    ("scan_line_flags", np.uint8, VIDEO_HEIGHT),
    ("audio", np.uint8, AUDIO_SIZE),
])

STATESAV_DTYPE = np.dtype([
    ("PC", '<u2'),
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ("unused1", np.uint8, 249),
    ("memory", np.uint8, MAIN_MEMORY_SIZE),
    ("hires_graphics", np.uint8),
    ("text_mode", np.uint8),
    ("mixed_mode", np.uint8),
    ("alt_page_select", np.uint8),
    ("tv_line", np.uint8),
    ("tv_cycle", np.uint8),
    ("unused2", np.uint8, 250),
    ])

CPU_DTYPE = np.dtype([
    ("PC", '<u2'),
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ("unused1", np.uint8, 249),
    ])
