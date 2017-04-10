# Standard library imports.
import os
import time
import wx

import logging
log = logging.getLogger(__name__)

class WindowLogHandler(logging.Handler):
    """
    A handler class which sends log strings to a wx object
    """

    def __init__(self, control):
        """
        Initialize the handler
        @param wxDest: the destination object to post the event to 
        @type wxDest: wx.Window
        """
        logging.Handler.__init__(self)
        self.level = logging.DEBUG
        self.control = control

    def flush(self):
        """
        does nothing for this handler
        """

    def emit(self, record):
        """
        Emit a record.

        """
        msg = self.format(record)
        wx.CallAfter(self.control.WriteText, msg + "\n")


if __name__ == '__main__':
    import random

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    LEVELS = [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL
    ]

    def onButton(event):
        logger.log(random.choice(LEVELS), "More? click again!")

    app = wx.App(redirect = False)
    frame = wx.Frame(None, title='Progress Test', size=(800,400))
    panel = wx.Panel(frame, wx.ID_ANY)
    log = wx.TextCtrl(panel, wx.ID_ANY, size=(300,100),
                      style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
    btn = wx.Button(panel, wx.ID_ANY, 'Log something!')
    frame.Bind(wx.EVT_BUTTON, onButton, btn)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(log, 1, wx.ALL|wx.EXPAND, 5)
    sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
    panel.SetSizer(sizer)
    handler = WindowLogHandler(log)
    logger.addHandler(handler)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(msg)s"))
    logger.setLevel(logging.DEBUG)
    frame.Show()
    app.MainLoop()
