import time

import numpy as np

from . import libatari800 as liba8
from . import dtypes as d
from . import akey
from .colors import NTSC
from ..emulator_base import EmulatorBase

import logging
log = logging.getLogger(__name__)


debug_frames = False

def clamp(val):
    if val < 0.0:
        return 0
    elif val > 255.0:
        return 255
    return int(val)

ntsc_iq_lookup = [
    [  0.000,  0.000 ],
    [  0.144, -0.189 ],
    [  0.231, -0.081 ],
    [  0.243,  0.032 ],
    [  0.217,  0.121 ],
    [  0.117,  0.216 ],
    [  0.021,  0.233 ],
    [ -0.066,  0.196 ],
    [ -0.139,  0.134 ],
    [ -0.182,  0.062 ],
    [ -0.175, -0.022 ],
    [ -0.136, -0.100 ],
    [ -0.069, -0.150 ],
    [  0.005, -0.159 ],
    [  0.071, -0.125 ],
    [  0.124, -0.089 ],
    ]

def gtia_ntsc_to_rgb_table(val):
    # This is a better representation of the NTSC colors using a lookup table
    # rather than the phase calculations. Also from the same thread:
    # http://atariage.com/forums/topic/107853-need-the-256-colors/page-2#entry1319398
    cr = (val >> 4) & 15;
    lm = val & 15;

    y = 255*(lm+1)/16;
    i = ntsc_iq_lookup[cr][0] * 255
    q = ntsc_iq_lookup[cr][1] * 255

    r = y + 0.956*i + 0.621*q;
    g = y - 0.272*i - 0.647*q;
    b = y - 1.107*i + 1.704*q;

    return clamp(r), clamp(g), clamp(b)

def ntsc_color_map():
    rmap = np.empty(256, dtype=np.uint8)
    gmap = np.empty(256, dtype=np.uint8)
    bmap = np.empty(256, dtype=np.uint8)

    for i in range(256):
        r, g, b = gtia_ntsc_to_rgb_table(i)
        rmap[i] = r
        gmap[i] = g
        bmap[i] = b

    return rmap, gmap, bmap


class Atari800(EmulatorBase):
    cpu = "6502"
    name = "atari800"
    pretty_name = "Atari 800"

    input_array_dtype = d.INPUT_DTYPE
    output_array_dtype = d.OUTPUT_DTYPE
    width = d.VIDEO_WIDTH
    height = d.VIDEO_HEIGHT

    low_level_interface = liba8

    mime_prefix = "application/vnd.atari8bit"

    def compute_color_map(self):
        self.rmap, self.gmap, self.bmap = ntsc_color_map()

    @property
    def current_cpu_status(self):
        a, p, sp, x, y, _, pc = self.cpu_state

        # Confirm validity by checking raw locations
        cpu_offset = self.output[0]['tag_cpu']
        registers = self.raw_state[cpu_offset:cpu_offset+5]
        assert a == registers[0]
        assert p == registers[1]
        assert sp == registers[2]
        assert x == registers[3]
        assert y == registers[4]
        raw_pc = self.raw_state[self.output[0]['tag_pc']:]
        assert pc == (raw_pc[0] + 256 * raw_pc[1])
        return "A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc)

    def process_args(self, emu_args):
        # FIXME: need to find a way to turn on/off carts outside of the init
        # routines because boot_from_file restarts the machine with the new
        # file but currently doesn't change cart status.
        if not emu_args:
            emu_args = [
                #"-basic",
                #"-shmem-debug-video",
                #"jumpman.atr"
            ]
        return emu_args

    def generate_save_state_memory_blocks(self):
        s = self.state_start_offset
        self.computed_dtypes = {
            'ANTIC': d.ANTIC_DTYPE,
            'GTIA': d.GTIA_DTYPE,
            'POKEY': d.POKEY_DTYPE,
            'PIA': d.PIA_DTYPE,
        }
        self.segment_starts = {
            'ANTIC': self.output[0]['tag_antic'],
            'GTIA': self.output[0]['tag_gtia'],
            'POKEY': self.output[0]['tag_pia'],
            'PIA': self.output[0]['tag_pokey'],
        }
        segments = [
            (s + self.output[0]['tag_cpu'], 6, 0, "CPU Regisers"),
            (s + self.output[0]['tag_base_ram'], 256*256, 0, "Main Memory"),
            (s + self.output[0]['tag_antic'], d.ANTIC_DTYPE.itemsize, 0, "ANTIC"),
            (s + self.output[0]['tag_gtia'], d.GTIA_DTYPE.itemsize, 0, "GTIA"),
            (s + self.output[0]['tag_pia'], d.PIA_DTYPE.itemsize, 0, "PIA"),
            (s + self.output[0]['tag_pokey'], d.POKEY_DTYPE.itemsize, 0, "POKEY"),
        ]
        self.save_state_memory_blocks.extend(segments)

    def boot_from_file(self, filename):
        log.debug(f"booting {self.pretty_name} from {filename}")
        liba8.reboot_with_file(filename)
        self.configure_io_arrays()

    def end_emulation(self):
        pass

    def debug_video(self):
        video_mem = self.output[0]['video'].view(dtype=np.uint8)
        offset = 336*24 + 8
        for y in range(32):
            print("%x:" % offset, end=' ')
            for x in range(8,60):
                c = video_mem[x + offset]
                if (c == 0 or c == '\x00'):
                    print(" ", end=' ')
                elif (c == 0x94 or c == '\x94'):
                    print(".", end=' ')
                elif (c == 0x9a or c == '\x9a'):
                    print("X", end=' ')
                else:
                    try:
                        print(ord(c), end=' ')
                    except TypeError:
                        print(repr(c), end=' ')
            print()
            offset += 336;

    def calc_cpu_data_array(self):
        cpu_offset = self.output[0]['tag_cpu']
        pc_offset = self.output[0]['tag_pc']
        computed_dtype = np.dtype([
            ("A", np.uint8),
            ("P", np.uint8),
            ("SP", np.uint8),
            ("X", np.uint8),
            ("Y", np.uint8),
            ("_", np.uint8, pc_offset - cpu_offset - 5),
            ("PC", '<u2'),
            ])
        raw = self.raw_state[cpu_offset:cpu_offset + computed_dtype.itemsize]
        print(("sizeof raw_array=%d raw=%d dtype=%d" % (len(self.raw_array), len(raw), computed_dtype.itemsize)))
        dataview = raw.view(dtype=computed_dtype)
        return dataview[0]

    def calc_dtype_data(self, segment_name):
        d = np.dtype(self.computed_dtypes[segment_name])
        start = self.segment_starts[segment_name]
        raw = self.raw_array[start:start + d.itemsize]
        return raw.view(dtype=d)[0]

    def calc_main_memory_array(self):
        offset = self.output[0]['tag_base_ram']
        return self.raw_array[offset:offset + 1<<16]

    # Emulator user input functions

    def coldstart(self):
        """Simulate an initial power-on startup.
        """
        self.send_special_key(akey.AKEY_COLDSTART)
        self.configure_io_arrays()

    def warmstart(self):
        """Simulate a warm start; i.e. pressing the system reset button
        """
        self.send_special_key(akey.AKEY_WARMSTART)
        self.configure_io_arrays()

    def keypress(self, ascii_char):
        self.send_char(ord(ascii_char))

    # Utility functions

    def get_color_indexed_screen(self, frame_number=-1):
        if frame_number < 0:
            output = self.output
        else:
            _, output = self.get_history(frame_number)
        raw = output['video'].reshape((self.height, self.width))
        #print "get_raw_screen", frame_number, raw
        return raw

    def get_frame_rgb(self, frame_number=-1):
        raw = self.get_color_indexed_screen(frame_number)
        self.screen_rgb[:,:,0] = self.rmap[raw]
        self.screen_rgb[:,:,1] = self.gmap[raw]
        self.screen_rgb[:,:,2] = self.bmap[raw]
        return self.screen_rgb

    def get_frame_rgba(self, frame_number=-1):
        raw = self.get_color_indexed_screen(frame_number)
        self.screen_rgba[:,:,0] = self.rmap[raw]
        self.screen_rgba[:,:,1] = self.gmap[raw]
        self.screen_rgba[:,:,2] = self.bmap[raw]
        self.screen_rgba[:,:,3] = 255
        return self.screen_rgba

    def get_frame_rgba_opengl(self, frame_number=-1):
        raw = np.flipud(self.get_color_indexed_screen(frame_number))
        self.screen_rgba[:,:,0] = self.rmap[raw]
        self.screen_rgba[:,:,1] = self.gmap[raw]
        self.screen_rgba[:,:,2] = self.bmap[raw]
        self.screen_rgba[:,:,3] = 255
        return self.screen_rgba

    ##### Input routines

    def send_special_key(self, key_id):
        self.input['keychar'] = 0
        self.input['keycode'] = 0
        self.input['special'] = key_id
        if key_id in [2, 3]:
            self.frame_event.append((self.frame_count + 2, self.clear_keys))

    def set_option(self, state):
        self.input['option'] = state

    def set_select(self, state):
        self.input['select'] = state

    def set_start(self, state):
        self.input['start'] = state

try:
    import wx

    class wxAtari800(Atari800):
        wx_to_akey = {
            wx.WXK_BACK: akey.AKEY_BACKSPACE,
            wx.WXK_DELETE: akey.AKEY_DELETE_CHAR,
            wx.WXK_INSERT: akey.AKEY_INSERT_CHAR,
            wx.WXK_ESCAPE: akey.AKEY_ESCAPE,
            wx.WXK_END: akey.AKEY_HELP,
            wx.WXK_HOME: akey.AKEY_CLEAR,
            wx.WXK_RETURN: akey.AKEY_RETURN,
            wx.WXK_SPACE: akey.AKEY_SPACE,
            wx.WXK_F7: akey.AKEY_BREAK,
            wx.WXK_PAUSE: akey.AKEY_BREAK,
            96: akey.AKEY_ATARI,  # back tick
        }

        wx_to_akey_ctrl = {
            wx.WXK_UP: akey.AKEY_UP,
            wx.WXK_DOWN: akey.AKEY_DOWN,
            wx.WXK_LEFT: akey.AKEY_LEFT,
            wx.WXK_RIGHT: akey.AKEY_RIGHT,
        }

        def process_key_down(self, evt, keycode):
            log.debug("key down! key=%s mod=%s" % (evt.GetKeyCode(), evt.GetModifiers()))
            key = evt.GetKeyCode()
            mod = evt.GetModifiers()
            if mod == wx.MOD_CONTROL:
                akey = self.wx_to_akey_ctrl.get(key, None)
            else:
                akey = self.wx_to_akey.get(key, None)

            if akey is None:
                evt.Skip()
            else:
                self.send_keycode(akey)

        def process_key_state(self):
            up = 0b0001 if wx.GetKeyState(wx.WXK_UP) else 0
            down = 0b0010 if wx.GetKeyState(wx.WXK_DOWN) else 0
            left = 0b0100 if wx.GetKeyState(wx.WXK_LEFT) else 0
            right = 0b1000 if wx.GetKeyState(wx.WXK_RIGHT) else 0
            self.input['joy0'] = up | down | left | right
            trig = 1 if wx.GetKeyState(wx.WXK_CONTROL) else 0
            self.input['trig0'] = trig
            #print "joy", self.emulator.input['joy0'], "trig", trig

            # console keys will reflect being pressed if at any time between frames
            # the key has been pressed
            self.input['option'] = 1 if wx.GetKeyState(wx.WXK_F2) or self.forced_modifier=='option' else 0
            self.input['select'] = 1 if wx.GetKeyState(wx.WXK_F3) or self.forced_modifier=='select' else 0
            self.input['start'] = 1 if wx.GetKeyState(wx.WXK_F4) or self.forced_modifier=='start' else 0

except ImportError:
    class wxAtari800(object):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("wx not available! Can't run wxAtari800")
