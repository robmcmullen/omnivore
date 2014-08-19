# Standard library imports.
import os
import wx
import wx.lib.newevent

# Enthought library imports.
from traits.api import HasTraits, on_trait_change, Any, Instance, List, Bool, Int, Range, Str, Unicode, Event
from envisage.api import ExtensionPoint, Plugin

# Local imports.
from peppy2.framework.plugin import FrameworkPlugin


import logging
log = logging.getLogger(__name__)

# wx logging handler from http://stackoverflow.com/questions/2819791/how-can-i-redirect-the-logger-to-a-wxpython-textctrl-using-a-custom-logging-hand
# create event type
wxLogEvent, EVT_WX_LOG_EVENT = wx.lib.newevent.NewEvent()


class ProgressDialog(wx.Dialog):
    def __init__(self, parent, title="Progress"):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=wx.DefaultSize, pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE)
        self.border = 20
        
        self.SetBackgroundColour(wx.WHITE)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.label = wx.StaticText(self, -1, "Loading...")
        self.label.SetBackgroundColour(wx.WHITE)
        sizer.Add(self.label, 0, flag=wx.EXPAND|wx.ALL, border=self.border)

        self.progressHeight = 12
        self.gauge = wx.Gauge(self, -1,
              range=100, size = (-1, self.progressHeight),
              style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        self.gauge.SetBackgroundColour(wx.WHITE)
        sizer.Add(self.gauge, 0, flag=wx.EXPAND|wx.ALL, border=self.border)

        self.count = 0

        self.visible = True
        self.is_pulse = True

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.label.Layout()
        self.gauge.Layout()
        self.Layout()
        self.CenterOnParent()

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
    
    
    def __init__(self):
        """
        Initialize the handler
        @param wxDest: the destination object to post the event to 
        @type wxDest: wx.Window
        """
        logging.Handler.__init__(self)
        self.level = logging.DEBUG

    def flush(self):
        """
        does nothing for this handler
        """

    def emit(self, record):
        """
        Emit a record.

        """
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
        if not cls.progress_dialog.IsShown():
            cls.progress_dialog.Show()
            wx.Yield()
        return cls.progress_dialog
    
    def post(self, evt):
        print "POSTING!!!!!! %s: %s" % (evt.levelname, evt.message)
        d = self.get_dialog()
        if evt.message == "START":
            wx.BeginBusyCursor()
            wx.Yield()
        elif evt.message == "END":
            wx.EndBusyCursor()
            d.Destroy()
            wx.Yield()
        elif evt.message.startswith("TICKS"):
            _, count = evt.message.split("=")
            d.set_ticks(int(count))
        elif evt.message == "PULSE":
            d.set_pulse()
        else:
            d.tick(evt.message)


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
        log = logging.getLogger("load")
        handler = wxLogHandler()
        log.addHandler(handler)
        
        log = logging.getLogger("save")
        handler = wxLogHandler()
        log.addHandler(handler)
