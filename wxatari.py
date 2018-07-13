#!/usr/bin/env python

import os
import sys
import time
import wx
import wx.lib.newevent
try:
    import wx.glcanvas as glcanvas
    import OpenGL.GL as gl
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False

# FIXME: OpenGL on wx4 is segfaulting.
# update: Legacy OpenGL is segfaulting, GLSL seems to work.
#HAS_OPENGL = False

import numpy as np

# Include pyatari directory so that modules can be imported normally
import sys
module_dir = os.path.realpath(os.path.abspath(".."))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)
import omni8bit.atari800 as a8
akey = a8.akey

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)




class EmulatorControlBase(object):
    def __init__(self, emulator):
        self.emulator_panel = None
        self.emulator = emulator

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)

        self.firsttime=True
        self.refreshed=False
        self.repeat=True
        self.forceupdate=False
        self.framerate = 1/60.0
        self.tickrate = self.framerate
        self.delay = self.tickrate * 1000  # wxpython delays are in milliseconds
        self.last_update_time = 0.0

        self.key_down = False

    def on_key_down(self, evt):
        log.debug("key down! key=%s mod=%s" % (evt.GetKeyCode(), evt.GetModifiers()))
        key = evt.GetKeyCode()
        mod = evt.GetModifiers()
        if mod == wx.MOD_ALT or self.is_paused:
            self.on_emulator_command_key(evt)
            return
        elif key == wx.WXK_F11:
            self.on_emulator_command_key(evt)
            return
        else:
            self.emulator.process_key_down_event(evt)
    
    def on_key_up(self, evt):
        log.debug("key up before evt=%s" % evt.GetKeyCode())
        key=evt.GetKeyCode()
        self.emulator.clear_keys()

        evt.Skip()

    def on_char(self, evt):
        log.debug("on_char! char=%s, key=%s, raw=%s modifiers=%s" % (evt.GetUnicodeKey(), evt.GetKeyCode(), evt.GetRawKeyCode(), bin(evt.GetModifiers())))
        mods = evt.GetModifiers()
        char = evt.GetUnicodeKey()
        if char > 0:
            self.emulator.send_char(char)
        else:
            key = evt.GetKeyCode()

        evt.Skip()

    def show_audio(self):
        #import binascii
        #a = binascii.hexlify(self.emulator.audio)
        #print np.where(self.emulator.audio > 0)
        pass

    # No really good solutions, especially cross-platform. In python 3, there's
    # time.perf_counter, so maybe that it a thread will work where the thread
    # generates wx Events that can be monitored.
    if True:
        def on_timer(self, evt):
            now = time.time()
            self.emulator.next_frame()
            print(f"showing frame {self.emulator.output['frame_number']} {self.emulator.current_cpu_status}")
            self.emulator_panel.show_frame()
            self.show_audio()

            after = time.time()
            delta = after - now
            if delta > self.framerate:
                next_time = self.framerate * .8
            elif delta < self.framerate:
                next_time = self.framerate - delta
            print(("now=%f show=%f delta=%f framerate=%f next_time=%f" % (now, after-now, delta, self.framerate, next_time)))
            self.timer.StartOnce(next_time * 1000)
            self.last_update_time = now
            evt.Skip()
    elif wx.Platform == "__WXGTK__":
        def on_timer(self, evt):
            if self.timer.IsRunning():
                self.process_key_state()
                now = time.time()
                delta = now - self.last_update_time
                print(("now=%f delta=%f framerate=%f" % (now, delta, self.framerate)))
                if delta >= self.framerate:
                    self.emulator.next_frame()
                    print(("showing frame %d" % self.emulator.output['frame_number']))
                    self.emulator_panel.show_frame()
                    self.show_audio()
                    if delta > 2 * self.framerate:
                        self.emulator.next_frame()
                        print(("got extra frame %d" % self.emulator.output['frame_number']))
                        self.emulator_panel.show_frame()
                        self.show_audio()
                        self.last_update_time = now  # + (delta % self.framerate)
                    else:
                        self.last_update_time += self.framerate
                else:
                    print(("pausing a tick after frame %d" % self.emulator.output['frame_number']))
                    #self.last_update_time += self.tickrate
            evt.Skip()
    elif wx.Platform == "__WXMSW__":
        # FIXME: settles on 120%
        def on_timer(self, evt):
            if self.timer.IsRunning():
                self.process_key_state()
                now = time.time()
                if now > self.next_update_time:
                    delta = now - self.next_update_time
                    print(("now=%f next=%f delta=%f framerate=%f" % (now, self.next_update_time, delta, self.framerate)))
                    self.emulator.next_frame()
                    self.emulator_panel.show_frame()
                    self.show_audio()

                    # updating too slowly?
                    self.frame_delta += delta
                    delta = now - self.next_update_time
                    if delta > self.framerate:
                        self.emulator.next_frame()
                        print(("got extra frame %d" % self.emulator.output['frame_number']))
                        self.emulator_panel.show_frame()
                        self.show_audio()
                        self.next_update_time += self.framerate
                    self.next_update_time += self.framerate
                else:
                    print(("pausing a tick after frame %d" % self.emulator.output['frame_number']))
                    #self.last_update_time += self.tickrate
            evt.Skip()

    def start_timer(self,repeat=False,delay=None,forceupdate=True):
        if not self.timer.IsRunning():
            self.repeat=repeat
            if delay is not None:
                self.delay=delay
            self.forceupdate=forceupdate
            self.last_update_time = time.time()
            self.next_update_time = time.time() + self.framerate
            self.frame_delta = 0.0
            self.timer.Start(self.delay)

    def stop_timer(self):
        if self.timer.IsRunning():
            self.timer.Stop()

    def on_start(self, evt=None):
        self.start_timer(repeat=True)

    @property
    def is_paused(self):
        return not self.timer.IsRunning()

    def on_pause(self, evt=None):
        self.stop_timer()


class EmulatorFrame(EmulatorControlBase, wx.Frame):
    parsed_args = []
    options = {}

    def __init__(self, bootfile=None, autostart=True):
        wx.Frame.__init__(self, None, -1, "wxPython atari800 test", pos=(50,50),
                         size=(200,100), style=wx.DEFAULT_FRAME_STYLE)
        EmulatorControlBase.__init__(self, a8.wxAtari800())

        self.CreateStatusBar()

        menuBar = wx.MenuBar()
        menu = wx.Menu()
        self.id_load = wx.NewId()
        item = menu.Append(self.id_load, "Load Image", "Load a disk image")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menu.AppendSeparator()
        item = menu.Append(wx.ID_EXIT, "E&xit\tCtrl-Q", "Exit demo")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menuBar.Append(menu, "&File")

        self.id_pause = wx.NewId()
        self.id_coldstart = wx.NewId()
        self.id_warmstart = wx.NewId()
        self.id_start_debugging = wx.NewId()
        self.id_debug_step = wx.NewId()
        menu = wx.Menu()
        self.pause_item = menu.Append(self.id_pause, "Pause\tCtrl-P", "Pause or resume the emulation")
        self.Bind(wx.EVT_MENU, self.on_menu, self.pause_item)
        item = menu.Append(self.id_start_debugging, "Start Debugging", "Enter monitor")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menu.AppendSeparator()
        item = menu.Append(self.id_debug_step, "Step", "Process one instruction")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menu.AppendSeparator()
        item = menu.Append(self.id_coldstart, "Cold Start", "Cold start (power switch off then on)")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        item = menu.Append(self.id_coldstart, "Warm Start", "Warm start (reset switch)")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menuBar.Append(menu, "&Machine")

        self.id_screen1x = wx.NewId()
        self.id_screen2x = wx.NewId()
        self.id_screen3x = wx.NewId()
        self.id_glsl = wx.NewId()
        self.id_opengl = wx.NewId()
        self.id_unaccelerated = wx.NewId()
        menu = wx.Menu()
        item = menu.AppendRadioItem(self.id_glsl, "GLSL", "Use GLSL for scalable display")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        item = menu.AppendRadioItem(self.id_opengl, "OpenGL", "Use OpenGL for scalable display")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        item = menu.AppendRadioItem(self.id_unaccelerated, "Unaccelerated", "No OpenGL acceleration")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menu.AppendSeparator()
        item = menu.Append(self.id_screen1x, "Display 1x", "No magnification")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        item = menu.Append(self.id_screen2x, "Display 2x", "2x display")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        item = menu.Append(self.id_screen3x, "Display 3x", "3x display")
        self.Bind(wx.EVT_MENU, self.on_menu, item)
        menuBar.Append(menu, "&Screen")

        self.SetMenuBar(menuBar)
        self.Show(True)
        self.Bind(wx.EVT_CLOSE, self.on_close_frame)

        self.SetSize((800, 600))

        self.emulator_panel = wx.Panel(self, -1)
        self.cpu_status = wx.StaticText(self, -1)

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.emulator_panel, 1, wx.EXPAND)
        self.box.Add(self.cpu_status, 0, wx.EXPAND)
        self.SetSizer(self.box)

        if self.options.unaccelerated or wx.Platform == "__WXMSW__":
            control = a8.BitmapScreen
        elif self.options.glsl and HAS_OPENGL:
            control = a8.GLSLScreen
        elif HAS_OPENGL:
            control = a8.OpenGLScreen
        else:
            control = a8.BitmapScreen
        self.set_display(control)

        self.frame_cursor = -1

        self.emulator.configure_emulator([])

        if self.parsed_args:
            self.emulator.boot_from_file(self.parsed_args[0])

        if autostart:
            wx.CallAfter(self.on_start, None)

    def set_glsl(self):
        self.set_display(a8.GLSLScreen)

    def set_opengl(self):
        self.set_display(a8.OpenGLScreen)

    def set_unaccelerated(self):
        self.set_display(a8.BitmapScreen)

    def set_display(self, panel_cls):
        paused = self.is_paused
        self.on_pause()
        old = self.emulator_panel

        # Mac can occasionally fail to get an OpenGL context, so creation of
        # the panel can fail. Attempting to work around by giving it more
        # chances to work.
        attempts = 3
        while attempts > 0:
            attempts -= 1
            try:
                self.emulator_panel = panel_cls(self, self.emulator)
                attempts = 0
            except wx.wxAssertionError:
                log.error("Failed initializing OpenGL context. Trying %d more times" % attempts)
                time.sleep(1)

        self.box.Replace(old, self.emulator_panel)
        old.Destroy()
        print(self.emulator_panel)
        self.Layout()
        self.emulator_panel.SetFocus()

        self.emulator_panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.emulator_panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.emulator_panel.Bind(wx.EVT_CHAR, self.on_char)

        if not paused:
            self.on_start()

    def on_menu(self, evt):
        id = evt.GetId()
        if id == wx.ID_EXIT:
            self.emulator.end_emulation()
            self.timer.Stop()
            self.Close(True)
        elif id == self.id_load:
            dlg = wx.FileDialog(self, "Choose a disk image", defaultDir = "", defaultFile = "", wildcard = "*.atr")
            if dlg.ShowModal() == wx.ID_OK:
                print(("Opening %s" % dlg.GetPath()))
                filename = dlg.GetPath()
            else:
                filename = None
            dlg.Destroy()
            if filename:
                self.emulator.load_disk(1, filename)
                self.emulator.coldstart()
        elif id == self.id_coldstart:
            self.emulator.coldstart()
        elif id == self.id_warmstart:
            self.emulator.warmstart()
        elif id == self.id_start_debugging:
            self.pause()
        elif id == self.id_debug_step:
            self.emulator.debugger_step()
        elif id == self.id_glsl:
            self.set_glsl()
        elif id == self.id_opengl:
            self.set_opengl()
        elif id == self.id_unaccelerated:
            self.set_unaccelerated()
        elif id == self.id_screen1x:
            self.emulator_panel.set_scale(1)
        elif id == self.id_screen2x:
            self.emulator_panel.set_scale(2)
        elif id == self.id_screen3x:
            self.emulator_panel.set_scale(3)
        elif id == self.id_pause:
            if self.is_paused:
                self.restart()
            else:
                self.pause()

    def on_emulator_command_key(self, evt):
        key = evt.GetKeyCode()
        mod = evt.GetModifiers()
        print(("emu key: %s %s" % (key, mod)))
        if key == wx.WXK_LEFT:
            if not self.is_paused:
                self.pause()
            else:
                self.history_previous()
        elif key == wx.WXK_RIGHT:
            if not self.is_paused:
                self.pause()
            else:
                self.history_next()
        elif key == wx.WXK_SPACE or key == wx.WXK_F11:
            if self.is_paused:
                self.restart()
            else:
                self.pause()

    def restart(self):
        print("restart")
        self.on_start()
        self.pause_item.SetItemLabel("Pause")
        if self.frame_cursor >= 0:
            self.emulator.restore_history(self.frame_cursor)
        self.frame_cursor = -1
        self.SetStatusText("")

    def pause(self):
        print("pause")
        self.on_pause()
        self.pause_item.SetItemLabel("Resume")
        self.update_ui()
    
    def history_previous(self):
        if self.frame_cursor < 0:
            self.frame_cursor = self.emulator.current_frame_number
        try:
            self.frame_cursor = self.emulator.get_previous_history(self.frame_cursor)
            #self.emulator.restore_history(frame_number)
        except IndexError:
            return
        self.emulator_panel.show_frame(self.frame_cursor)
        self.update_ui()
    
    def history_next(self):
        if self.frame_cursor < 0:
            return
        try:
            self.frame_cursor = self.emulator.get_next_history(self.frame_cursor)
            #self.emulator.restore_history(frame_number)
        except IndexError:
            self.frame_cursor = -1
        self.emulator_panel.show_frame(self.frame_cursor)
        self.update_ui()

    def show_frame_number(self):
        text = "Paused: %d frames, showing %d" % (self.emulator.current_frame_number, self.frame_cursor if self.frame_cursor > 0 else self.emulator.current_frame_number)
        print(text)
        self.SetStatusText(text)

    def update_ui(self):
        self.show_frame_number()
        self.update_internals()

    def update_internals(self):
        a, p, sp, x, y, _, pc = self.emulator.cpu_state
        #print(offsets)
        text = "A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc)
        self.cpu_status.SetLabel(text)

    def on_close_frame(self, evt):
        self.emulator.end_emulation()
        evt.Skip()



if __name__ == '__main__':
    # use argparse rather than sys.argv to handle the difference in being
    # called as "python script.py" and "./script.py"
    import argparse

    parser = argparse.ArgumentParser(description='Atari800 WX Demo')
    parser.add_argument("--unaccelerated", "--bitmap", "--slow", action="store_true", default=False, help="Use bitmap scaling instead of OpenGL")
    parser.add_argument("--opengl", action="store_true", default=False, help="Use OpenGL scaling")
    parser.add_argument("--glsl", action="store_true", default=False, help="Use GLSL scaling")
    EmulatorFrame.options, EmulatorFrame.parsed_args = parser.parse_known_args()
    app = wx.App(False)
    frame = EmulatorFrame()
    frame.Show()
    app.MainLoop()
