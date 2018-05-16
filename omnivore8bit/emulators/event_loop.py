import wx


class MonitorEventLoop(wx.GUIEventLoop):
    def __init__(self):
        wx.GUIEventLoop.__init__(self)
        self.exitCode = 0
        self.shouldExit = False
        self.count = 0

    def DoMyStuff(self):
        # Do whatever you want to have done for each iteration of the event
        # loop. In this example we'll just sleep a bit to simulate something
        # real happening.
        #time.sleep(0.10)
        self.count += 1
        print "\rhihihi %d" % self.count,
        # time.sleep(0.02)

    def Run(self):
        # Set this loop as the active one. It will automatically reset to the
        # original evtloop when the context manager exits.
        print("Starting alternate event loop")
        app = wx.GetApp()
        with wx.EventLoopActivator(self):
            while True:

                self.DoMyStuff()

                # Generate and process idles events for as long as there
                # isn't anything else to do
                while not self.shouldExit and not self.Pending() and self.ProcessIdle():
                    pass

                if self.shouldExit:
                    print("exiting alternate event loop")
                    break

                # dispatch all the pending events and call Dispatch() to wait
                # for the next message
                if not self.ProcessEvents():
                    break

                if app.HasPendingEvents():
                    app.ProcessPendingEvents()

                # Currently on wxOSX Pending always returns true, so the
                # ProcessIdle above is not ever called. Call it here instead.
                if 'wxOSX' in wx.PlatformInfo:
                    self.ProcessIdle()

            # Proces remaining queued messages, if any
            while True:
                checkAgain = False
                if wx.GetApp() and wx.GetApp().HasPendingEvents():
                    wx.GetApp().ProcessPendingEvents()
                    checkAgain = True
                if 'wxOSX' not in wx.PlatformInfo and self.Pending():
                    self.Dispatch()
                    checkAgain = True
                if not checkAgain:
                    break

        return self.exitCode


    def Exit(self, rc=0):
        print("requesting exit of alternate event loop")
        self.exitCode = rc
        self.shouldExit = True
        self.OnExit()
        self.WakeUp()


    def ProcessEvents(self):
        if wx.GetApp():
            wx.GetApp().ProcessPendingEvents()

        if self.shouldExit:
            return False

        return self.Dispatch()


active_event_loop = None


def start_monitor(document):
    global active_event_loop

    emu = document.emulator
    document.stop_timer()
    emu.get_current_state()
    document.emulator_update_screen_event = True
    document.emulator_update_info_event = True
    a, p, sp, x, y, _, pc = emu.cpu_state
    print("A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc))
    active_event_loop = MonitorEventLoop()
    emu.active_event_loop = active_event_loop
    active_event_loop.Run()
    emu.active_event_loop = None
    active_event_loop = None
