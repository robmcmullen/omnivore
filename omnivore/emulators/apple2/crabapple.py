import ctypes
import time

import numpy as np
np.set_printoptions(formatter={'int':hex})

try:
    import wx
except ImportError:
    wx = None

from ...utils import apple2util as a2

from ..generic6502 import lib6502, Generic6502
from ..generic6502 import dtypes as d

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


debug_frames = False


def a2_color_map():
    rmap = np.zeros(256, dtype=np.uint8)
    gmap = np.zeros(256, dtype=np.uint8)
    bmap = np.zeros(256, dtype=np.uint8)

    rmap[1] = 255
    gmap[1] = 255
    bmap[1] = 255

    return rmap, gmap, bmap


class Crabapple(Generic6502):
    cpu = "6502"
    name = "crabapple"
    ui_name = "Crabapple 2+"

    width = 560
    height = 384

    supported_filesystems = []
    supported_binaries = ["Apple DOS 3.3 Object File"]

    def configure_emulator_defaults(self):
        lib6502.set_a2_emulation_mode(1)

    def generate_save_state_memory_blocks(self):
        cpu_offset = self.state_start_offset
        memory_offset = cpu_offset + d.CPU_DTYPE.itemsize
        video_offset = cpu_offset + d.STATESAV_MAX_SIZE
        segments = [
            (cpu_offset, d.CPU_DTYPE.itemsize, 0, "CPU Status"),
            (memory_offset, d.MAIN_MEMORY_SIZE, 0, "Main Memory"),
            (memory_offset + 0x400, 0x400, 0x400, "Text/Lo-res Page 1"),
            (memory_offset + 0x800, 0x400, 0x800, "Text/Lo-res Page 2"),
            (memory_offset + 0x2000, 0x2000, 0x2000, "Hi-res Page 1"),
            (memory_offset + 0x4000, 0x2000, 0x4000, "Hi-res Page 2"),
            (video_offset, d.VIDEO_SIZE, 0, "Video RAM"),
            (video_offset + d.VIDEO_SIZE, d.VIDEO_HEIGHT, 0, "Scan Line Type"),
        ]
        self.save_state_memory_blocks.extend(segments)

    def compute_color_map(self):
        self.rmap, self.gmap, self.bmap = a2_color_map()

    def get_color_indexed_screen(self, frame_number=-1):
        if frame_number < 0:
            output = self.output
        else:
            _, output = self.get_history(frame_number)
        doubled = np.empty((384, 40), dtype=np.uint8)
        source = output['video'].reshape((192, 40))
        doubled[::2,:] = source
        doubled[1::2,:] = source
        raw = np.empty(self.height * self.width, dtype=np.uint8)
        a2.to_560_bw_pixels(doubled, raw)
        #print "get_raw_screen", frame_number, raw
        return raw.reshape((self.height, self.width))

    def get_frame_rgb(self, frame_number=-1):
        raw = self.get_color_indexed_screen(frame_number)
        self.screen_rgb[:,:,0] = self.rmap[raw]
        self.screen_rgb[:,:,1] = self.gmap[raw]
        self.screen_rgb[:,:,2] = self.bmap[raw]
        return self.screen_rgb

    if wx is not None:
        def process_key_down(self, evt, keycode):
            log.debug("key down! key=%s mod=%s" % (evt.GetKeyCode(), evt.GetModifiers()))
            key = evt.GetKeyCode()
            if key > 96 and key < 123:
                key -= 32
            elif key == wx.WXK_UP:
                key = 0x8b
            elif key == wx.WXK_DOWN:
                key = 0x8a
            elif key == wx.WXK_LEFT:
                key = 0x88
            elif key == wx.WXK_RIGHT:
                key = 0x95
            key |= 0x80
            self.send_char(key)
