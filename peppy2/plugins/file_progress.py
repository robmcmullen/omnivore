# Standard library imports.
import os
import wx
import wx.lib.newevent

# Enthought library imports.
from traits.api import HasTraits, on_trait_change, Any, Instance, List, Bool, Int, Range, Str, Unicode, Event
from envisage.api import ExtensionPoint, Plugin

# Local imports.
from peppy2.framework.plugin import FrameworkPlugin
from peppy2.framework.errors import ProgressCancelError

import logging
log = logging.getLogger(__name__)

# wx logging handler from http://stackoverflow.com/questions/2819791/how-can-i-redirect-the-logger-to-a-wxpython-textctrl-using-a-custom-logging-hand
# create event type
wxLogEvent, EVT_WX_LOG_EVENT = wx.lib.newevent.NewEvent()


class ProgressDialog(wx.Dialog):
    def __init__(self, parent, title="Progress", delay=1000):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=wx.DefaultSize, pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE)
        self.border = 20
        self.delay = delay
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.label = wx.StaticText(self, -1, "Working...")
        self.label.SetMinSize((400, -1))
        sizer.Add(self.label, 0, flag=wx.EXPAND|wx.ALL, border=self.border)

        self.progressHeight = 12
        self.gauge = wx.Gauge(self, -1,
              range=100, size = (-1, self.progressHeight),
              style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        sizer.Add(self.gauge, 0, flag=wx.EXPAND|wx.ALL, border=self.border)

        self.count = 0

        self.visible = False
        self._delaytimer = wx.PyTimer(self.on_timer)
        self.is_pulse = True

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_CANCEL)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, flag=wx.EXPAND|wx.ALL, border=5)
        btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.request_cancel = False

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.label.Layout()
        self.gauge.Layout()
        self.Layout()
        self.CenterOnParent()

    def on_cancel(self, evt):
        self.request_cancel = True
    
    def raise_error(self):
        raise ProgressCancelError(self.GetTitle() + " canceled by user!")

    def start_visibility_timer(self):
        if not self._delaytimer.IsRunning():
            self._delaytimer.Start(self.delay, oneShot=True)

    def on_timer(self):
        self.Show()

    def set_ticks(self, count):
        """Set the total number of ticks that will be contained in the
        progress bar.
        """
        self.gauge.SetRange(count)
        self.is_pulse = False

    def set_pulse(self):
        """Set the total number of ticks that will be contained in the
        progress bar.
        """
        self.gauge.Pulse()
        self.is_pulse = True
        wx.Yield()

    def tick(self, text):
        """Advance the progress bar by one tick and update the label.
        """
        self.label.SetLabel(text)
        if self.is_pulse:
            self.gauge.Pulse()
        else:
            self.count += 1
            self.gauge.SetValue(self.count)
        self.gauge.Update()
        wx.Yield()


class wxLogHandler(logging.Handler):
    """
    A handler class which sends log strings to a wx object
    """
    
    progress_dialog = None
    
    
    def __init__(self, default_title=""):
        """
        Initialize the handler
        @param wxDest: the destination object to post the event to 
        @type wxDest: wx.Window
        """
        logging.Handler.__init__(self)
        self.level = logging.DEBUG
        self.default_title = default_title
        self.disabled = None

    def flush(self):
        """
        does nothing for this handler
        """

    def emit(self, record):
        """
        Emit a record.

        """
        # Handle progress cancel request here, the only place that's not inside
        # a wx event handler.  Attempting to handle inside an event handler
        # doesn't propagate outside the event handler.
        d = self.__class__.progress_dialog
        if d and d.request_cancel:
            # change flag so the END command can be processed by post()
            d.request_cancel = False
            raise ProgressCancelError(d.GetTitle() + " canceled by user!")
        
        try:
            msg = self.format(record)
            evt = wxLogEvent(message=msg,levelname=record.levelname)
            self.post(evt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
    
    @classmethod
    def get_dialog(cls):
        if cls.progress_dialog is None or not cls.progress_dialog:
            top = wx.GetApp().GetTopWindow()
            cls.progress_dialog = ProgressDialog(top)
        return cls.progress_dialog
    
    def force_cursor(self):
        # OS X resets the busy cursor when the cursor moves out of the dialog,
        # so at every tick call this method to reset it to the wait cursor.
        # Other platforms don't have this problem.
        wx.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
    
    def post(self, evt):
        d = self.get_dialog()
        m = evt.message
        if m.startswith("START"):
            # Forcibly disable all windows (other than the progress dialog) to
            # prevent user event processing in the wx.Yield calls.
            self.disabler = wx.WindowDisabler(d)
            wx.BeginBusyCursor()
            if "=" in m:
                _, text = m.split("=")
                d.SetTitle(text)
            else:
                d.SetTitle(self.default_title)
            d.start_visibility_timer()
            wx.Yield()
        elif m.startswith("TITLE"):
            self.force_cursor()
            _, text = m.split("=")
            d.SetTitle(text)
            wx.Yield()
        elif m == "END":
            wx.EndBusyCursor()
            self.disabler = None
            d.Destroy()
            wx.Yield()
        elif m.startswith("TICKS"):
            self.force_cursor()
            _, count = m.split("=")
            d.set_ticks(int(count))
        elif m == "PULSE":
            self.force_cursor()
            d.set_pulse()
        else:
            self.force_cursor()
            d.tick(m)


class FileProgressPlugin(FrameworkPlugin):
    """wx dialog to monitor file load/save through the logging framework
    
    """

    wx_dialog = None

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'file_progress'

    # The plugin's name (suitable for displaying to the user).
    name = 'Recently Opened Files List'

    def start(self):
        log = logging.getLogger("progress")
        handler = wxLogHandler("Progress")
        log.addHandler(handler)
