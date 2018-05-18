import ctypes
import time

import numpy as np

from . import libatari800 as liba8
from . import generic_interface as g
from . import akey
from .save_state_parser import parse_state
from .colors import NTSC
from ..emulator_base import EmulatorBase

import logging
logging.basicConfig(level=logging.WARNING)
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


def start_monitor_event_loop(emu):
    print("Monitor event loop here!")
    liba8.get_current_state(emu.output)
    a, p, sp, x, y, _, pc = emu.cpu_state
    print(("A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc)))

    # Confirm validity by checking raw locations
    emu.debug_state()
    liba8.monitor_step()
    #time.sleep(.5)


class Atari800(EmulatorBase):
    cpu = "6502"
    name = "atari800"
    pretty_name = "Atari 800"

    input_array_dtype = g.INPUT_DTYPE
    output_array_dtype = g.OUTPUT_DTYPE
    width = g.VIDEO_WIDTH
    height = g.VIDEO_HEIGHT

    low_level_interface = liba8

    # atari800 will call the debugger at the next CPU_GO call, so the timer
    # must not stop here.
    stop_timer_for_debugger = False

    def compute_color_map(self):
        self.rmap, self.gmap, self.bmap = ntsc_color_map()

    @property
    def raw_array(self):
        return self.output.view(dtype=np.uint8)

    @property
    def video_array(self):
        return self.output['video'][0]

    @property
    def audio_array(self):
        return self.output['audio'][0]

    @property
    def state_array(self):
        return self.output['state'][0]

    @property
    def current_frame_number(self):
        return self.output['frame_number'][0]

    def configure_event_loop(self, event_loop=None, event_loop_args=None, *args, **kwargs):
        if event_loop is None:
            event_loop = start_monitor_event_loop
        if event_loop_args is None:
            event_loop_args = self
        return event_loop, event_loop_args

    def process_args(self, emu_args):
        if emu_args is None:
            emu_args = [
                "-basic",
                #"-shmem-debug-video",
                #"jumpman.atr"
            ]
        return emu_args

    def generate_extra_segments(self):
        self.offsets, self.names, extra_segments, self.segment_starts, self.computed_dtypes = parse_state(self.output['state'], self.state_start_offset)
        self.segments.extend(extra_segments)

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

    def debug_state(self):
        a, p, sp, x, y, _, pc = self.cpu_state

        # Confirm validity by checking raw locations
        names = self.names
        raw = self.raw_array
        assert a == raw[names['CPU_A']]
        assert p == raw[names['CPU_P']]
        assert sp == raw[names['CPU_S']]
        assert x == raw[names['CPU_X']]
        assert y == raw[names['CPU_Y']]
        assert pc == (raw[names['PC']] + 256 * raw[names['PC'] + 1])
        print(("A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc)))

    def calc_cpu_data_array(self):
        names = self.names
        computed_dtype = np.dtype([
            ("A", np.uint8),
            ("P", np.uint8),
            ("SP", np.uint8),
            ("X", np.uint8),
            ("Y", np.uint8),
            ("_", np.uint8, names['PC'] - names['CPU_A'] - 5),
            ("PC", '<u2'),
            ])
        raw = self.raw_array[names['CPU_A']:names['CPU_A'] + computed_dtype.itemsize]
        print(("sizeof raw_array=%d raw=%d dtype=%d" % (len(self.raw_array), len(raw), computed_dtype.itemsize)))
        dataview = raw.view(dtype=computed_dtype)
        return dataview[0]

    def calc_dtype_data(self, segment_name):
        d = np.dtype(self.computed_dtypes[segment_name])
        start = self.segment_starts[segment_name]
        raw = self.raw_array[start:start + d.itemsize]
        return raw.view(dtype=d)[0]

    def calc_main_memory_array(self):
        offset = self.names['ram_ram']
        return self.raw_array[offset:offset + 1<<16]

    # Emulator user input functions

    def coldstart(self):
        """Simulate an initial power-on startup.
        """
        self.send_special_key(akey.AKEY_COLDSTART)

    def warmstart(self):
        """Simulate a warm start; i.e. pressing the system reset button
        """
        self.send_special_key(akey.AKEY_WARMSTART)

    def keypress(self, ascii_char):
        self.send_char(ord(ascii_char))

    # Utility functions

    def get_color_indexed_screen(self, frame_number=-1):
        if frame_number < 0:
            output = self.output
        else:
            output = self.history[frame_number]
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

    def send_char(self, key_char):
        self.input['keychar'] = key_char
        self.input['keycode'] = 0
        self.input['special'] = 0

    def send_keycode(self, keycode):
        self.input['keychar'] = 0
        self.input['keycode'] = keycode
        self.input['special'] = 0

    def send_special_key(self, key_id):
        self.input['keychar'] = 0
        self.input['keycode'] = 0
        self.input['special'] = key_id
        if key_id in [2, 3]:
            self.frame_event.append((self.frame_count + 2, self.clear_keys))

    def clear_keys(self):
        self.input['keychar'] = 0
        self.input['keycode'] = 0
        self.input['special'] = 0

    def set_option(self, state):
        self.input['option'] = state

    def set_select(self, state):
        self.input['select'] = state

    def set_start(self, state):
        self.input['start'] = state

    def process_key_state(self):
        pass

    ##### debugger convenience functions

    def enter_debugger(self):
        if self.active_event_loop is not None:
            print("Only one debugger may be active at a time!")
        else:
            print("Requesting debugger start via AKEY_UI")
            # We don't enter the debugger directly because of the way the
            # debugger is called in atari800: in ANTIC_Frame in antic.c there
            # are many calls to the CPU_GO function and the breakpoints are
            # checked there. Using longjmp/setjmp it's easy to intercept each
            # call and send it back out the normal next_frame loop, but there's
            # no way to continue back where it was because we'd have to jump in
            # to the middle of ANTIC_Frame.
            #
            # So we have to use the normal atari800 way which is a call through
            # to PLATFORM_Exit, which calls the monitor routines. In
            # libatari800, it calls start_monitor_event_loop which is set up
            # above in configure_event_loop.
            self.send_special_key(akey.AKEY_UI)

    def restart_cpu(self):
        if self.active_event_loop is not None:
            self.clear_keys()
            self.active_event_loop.Exit()
            print("alternate event loop is over.")
            self.active_event_loop = None
            liba8.monitor_summary()

    def is_debugger_finished(self):
        # The debugger always finishes after each step because atari800 needs
        # to go back to normal processing to resume where it left off in
        # ANTIC_Frame.
        self.restart_cpu()
        return True

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

        def process_key_down_event(self, evt):
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
            self.input['option'] = 1 if wx.GetKeyState(wx.WXK_F2) else 0
            self.input['select'] = 1 if wx.GetKeyState(wx.WXK_F3) else 0
            self.input['start'] = 1 if wx.GetKeyState(wx.WXK_F4) else 0

except ImportError:
    class wxAtari800(object):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("wx not available! Can't run wxAtari800")
