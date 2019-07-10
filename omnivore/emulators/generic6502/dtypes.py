# generic6502 input template locations
import numpy as np

VIDEO_WIDTH = 280
VIDEO_HEIGHT = 192

VIDEO_SIZE = VIDEO_WIDTH * VIDEO_HEIGHT
AUDIO_SIZE = 2048
MAIN_MEMORY_SIZE = 1<<16
STATESAV_MAX_SIZE = MAIN_MEMORY_SIZE + 256


INPUT_DTYPE = np.dtype([
    ("keychar", np.uint8),
    ("keycode", np.uint8),
    ("special", np.uint8),
    ("shift", np.uint8),
    ("control", np.uint8),
])

OUTPUT_DTYPE = np.dtype([
    ("state", np.uint8, STATESAV_MAX_SIZE),
    ("video", np.uint8, VIDEO_SIZE),
    ("audio", np.uint8, AUDIO_SIZE),
])

STATESAV_DTYPE = np.dtype([
    ("PC", '<u2'),
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ("memory", np.uint8, MAIN_MEMORY_SIZE),
    ])

CPU_DTYPE = np.dtype([
    ("PC", '<u2'),
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ])
