# SHMEM input template locations
import numpy as np

VIDEO_WIDTH = 336
VIDEO_HEIGHT = 240

VIDEO_SIZE = VIDEO_WIDTH * VIDEO_HEIGHT
AUDIO_SIZE = 2048
STATESAV_MAX_SIZE = 210000

INPUT_DTYPE = np.dtype([
    ("keychar", np.uint8),
    ("keycode", np.uint8),
    ("special", np.uint8),
    ("shift", np.uint8),
    ("control", np.uint8),
    ("start", np.uint8),
    ("select", np.uint8),
    ("option", np.uint8),
    ("joy0", np.uint8),
    ("trig0", np.uint8),
    ("joy1", np.uint8),
    ("trig1", np.uint8),
    ("joy2", np.uint8),
    ("trig2", np.uint8),
    ("joy3", np.uint8),
    ("trig3", np.uint8),
    ("mousex", np.uint8),
    ("mousey", np.uint8),
    ("mouse_buttons", np.uint8),
    ("mouse_mode", np.uint8),
])

OUTPUT_DTYPE = np.dtype([
    ("frame_number", np.uint32),
    ("video", np.uint8, VIDEO_SIZE),
    ("audio", np.uint8, AUDIO_SIZE),
    ("state", np.uint8, STATESAV_MAX_SIZE),
])

CPU_DTYPE = np.dtype([
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ("PC", '<u2'),
    ])
