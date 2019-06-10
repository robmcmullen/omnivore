import time

import numpy as np

from . import libatari800 as liba8
from . import dtypes as d
from . import akey
from .colors import NTSC
from ..emulator_base import EmulatorBase
from ...errors import FrameNotFinishedError

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
    ui_name = "Atari 800"

    input_array_dtype = d.INPUT_DTYPE
    output_array_dtype = d.OUTPUT_DTYPE
    width = d.VIDEO_WIDTH
    height = d.VIDEO_HEIGHT

    low_level_interface = liba8

    mime_types = set(["application/vnd.atari8bit.atr", "application/vnd.atari8bit.xex", "application/vnd.atari8bit.cart", "application/vnd.atari8bit.atr.jumpman_level_tester",])

    # mime_prefix = "application/vnd.atari8bit"

    def serialize_to_dict(self):
        if not self.is_frame_finished:
            raise FrameNotFinishedError("atari800 can't save its internal state in the middle of a frame.")
        return EmulatorBase.serialize_to_dict(self)

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

    @property
    def program_counter(self):
        a, p, sp, x, y, _, pc = self.cpu_state
        return pc

    @property
    def current_antic_status(self):
        antic_offset = self.output[0]['tag_antic']
        registers = self.raw_state[antic_offset:antic_offset+d.ANTIC_DTYPE.itemsize]
        return f"antic: {str(registers)}"

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
        for name in self.output[0].dtype.names:
            print(f"offsets: output[{name}] = {self.output[0][name]}")

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
        log.debug(f"booting {self.ui_name} from {filename}")
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
        raw = self.raw_state[start:start + d.itemsize]
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

    def get_special_key_actions(self):
        return [
            "emu_a8_start_key",
            "emu_a8_select_key",
            "emu_a8_option_key",
        ]

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


class Atari800XL(Atari800):
    cpu = "6502"
    name = "atari800xl"
    ui_name = "Atari 800XL"

    def process_args(self, emu_args):
        if not emu_args:
            emu_args = [
                "-xl",
            ]
        return emu_args


class Atari5200(Atari800):
    cpu = "6502"
    name = "atari5200"
    ui_name = "Atari 5200"

    mime_types = set(["application/vnd.atari5200.cart",])

    def process_args(self, emu_args):
        if not emu_args:
            emu_args = [
                "-5200",
            ]
        return emu_args


try:
    import wx

    class wxMixin:
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
            65: akey.AKEY_a,
            66: akey.AKEY_b,
            67: akey.AKEY_c,
            68: akey.AKEY_d,
            69: akey.AKEY_e,
            70: akey.AKEY_f,
            71: akey.AKEY_g,
            72: akey.AKEY_h,
            73: akey.AKEY_i,
            74: akey.AKEY_j,
            75: akey.AKEY_k,
            76: akey.AKEY_l,
            77: akey.AKEY_m,
            78: akey.AKEY_n,
            79: akey.AKEY_o,
            80: akey.AKEY_p,
            81: akey.AKEY_q,
            82: akey.AKEY_r,
            83: akey.AKEY_s,
            84: akey.AKEY_t,
            85: akey.AKEY_u,
            86: akey.AKEY_v,
            87: akey.AKEY_w,
            88: akey.AKEY_x,
            89: akey.AKEY_y,
            90: akey.AKEY_z,
            48: akey.AKEY_0,
            49: akey.AKEY_1,
            50: akey.AKEY_2,
            51: akey.AKEY_3,
            52: akey.AKEY_4,
            53: akey.AKEY_5,
            54: akey.AKEY_6,
            55: akey.AKEY_7,
            56: akey.AKEY_8,
            57: akey.AKEY_9,
        }

        wx_to_akey_shift = {
            65: akey.AKEY_A,
            66: akey.AKEY_B,
            67: akey.AKEY_C,
            68: akey.AKEY_D,
            69: akey.AKEY_E,
            70: akey.AKEY_F,
            71: akey.AKEY_G,
            72: akey.AKEY_H,
            73: akey.AKEY_I,
            74: akey.AKEY_J,
            75: akey.AKEY_K,
            76: akey.AKEY_L,
            77: akey.AKEY_M,
            78: akey.AKEY_N,
            79: akey.AKEY_O,
            80: akey.AKEY_P,
            81: akey.AKEY_Q,
            82: akey.AKEY_R,
            83: akey.AKEY_S,
            84: akey.AKEY_T,
            85: akey.AKEY_U,
            86: akey.AKEY_V,
            87: akey.AKEY_W,
            88: akey.AKEY_X,
            89: akey.AKEY_Y,
            90: akey.AKEY_Z,
        }

        wx_to_akey_ctrl = {
            wx.WXK_UP: akey.AKEY_UP,
            wx.WXK_DOWN: akey.AKEY_DOWN,
            wx.WXK_LEFT: akey.AKEY_LEFT,
            wx.WXK_RIGHT: akey.AKEY_RIGHT,
            65: akey.AKEY_CTRL_a,
            66: akey.AKEY_CTRL_b,
            67: akey.AKEY_CTRL_c,
            68: akey.AKEY_CTRL_d,
            69: akey.AKEY_CTRL_e,
            70: akey.AKEY_CTRL_f,
            71: akey.AKEY_CTRL_g,
            72: akey.AKEY_CTRL_h,
            73: akey.AKEY_CTRL_i,
            74: akey.AKEY_CTRL_j,
            75: akey.AKEY_CTRL_k,
            76: akey.AKEY_CTRL_l,
            77: akey.AKEY_CTRL_m,
            78: akey.AKEY_CTRL_n,
            79: akey.AKEY_CTRL_o,
            80: akey.AKEY_CTRL_p,
            81: akey.AKEY_CTRL_q,
            82: akey.AKEY_CTRL_r,
            83: akey.AKEY_CTRL_s,
            84: akey.AKEY_CTRL_t,
            85: akey.AKEY_CTRL_u,
            86: akey.AKEY_CTRL_v,
            87: akey.AKEY_CTRL_w,
            88: akey.AKEY_CTRL_x,
            89: akey.AKEY_CTRL_y,
            90: akey.AKEY_CTRL_z,
        }

        def process_key_down(self, evt, keycode):
            log.debug("key down! key=%s mod=%s" % (evt.GetKeyCode(), evt.GetModifiers()))
            key = evt.GetKeyCode()
            mod = evt.GetModifiers()
            if mod == wx.MOD_CONTROL:
                akey = self.wx_to_akey_ctrl.get(key, None)
            elif mod == wx.MOD_SHIFT:
                akey = self.wx_to_akey_shift.get(key, None)
            else:
                akey = self.wx_to_akey.get(key, None)

            if akey is None:
                evt.Skip()
            else:
                self.send_keycode(akey)

        def process_key_state(self):
            try:
                up = 0b0001 if wx.GetKeyState(wx.WXK_UP) else 0
            except wx._core.PyNoAppError:
                return
            down = 0b0010 if wx.GetKeyState(wx.WXK_DOWN) else 0
            left = 0b0100 if wx.GetKeyState(wx.WXK_LEFT) else 0
            right = 0b1000 if wx.GetKeyState(wx.WXK_RIGHT) else 0
            self.input['joy0'] = up | down | left | right
            trig = 1 if wx.GetKeyState(wx.WXK_TAB) else 0
            self.input['trig0'] = trig
            # print("joy", self.input['joy0'], "trig", self.input['trig0'])

            # console keys will reflect being pressed if at any time between frames
            # the key has been pressed
            self.input['option'] = 1 if wx.GetKeyState(wx.WXK_F2) or self.forced_modifier=='option' else 0
            self.input['select'] = 1 if wx.GetKeyState(wx.WXK_F3) or self.forced_modifier=='select' else 0
            self.input['start'] = 1 if wx.GetKeyState(wx.WXK_F4) or self.forced_modifier=='start' else 0

    class wxAtari800(wxMixin, Atari800):
        pass

    class wxAtari800XL(wxMixin, Atari800XL):
        pass

    class wxAtari5200(wxMixin, Atari5200):
        pass


except ImportError:
    class wxAtari800:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("wx not available! Can't run wxAtari800")
    class wxAtari800XL:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("wx not available! Can't run wxAtari800XL")
    class wxAtari5200:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("wx not available! Can't run wxAtari5200")
