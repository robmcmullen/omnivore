#!/usr/bin/env python
import mock

import numpy as np

import wx

from omnivore.ui.bitviewscroller import BitviewScroller

if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Test', size=(500,500))
    frame.CreateStatusBar()

    panel = BitviewScroller(frame)
    bytes = np.arange(256, dtype=np.uint8)
    panel.set_data(bytes)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)

    def buttonHandler(evt):
        id = evt.GetId()
        if id == 100:
            panel.zoom_in()
        elif id == 101:
            panel.zoom_out()
        elif id == 200:
            wildcard="*"
            dlg = wx.FileDialog(
                frame, message="Open File",
                defaultFile="", wildcard=wildcard, style=wx.OPEN)

            # Show the dialog and retrieve the user response. If it is the
            # OK response, process the data.
            if dlg.ShowModal() == wx.ID_OK:
                # This returns a Python list of files that were selected.
                paths = dlg.GetPaths()

                for path in paths:
                    dprint("open file %s:" % path)
                    fh = open(path, 'rb')
                    img = wx.EmptyImage()
                    if img.LoadStream(fh):
                        panel.setImage(img)
                    else:
                        dprint("Invalid image: %s" % path)
            # Destroy the dialog. Don't do this until you are done with it!
            # BAD things can happen otherwise!
            dlg.Destroy()
        elif id == 201:
            pass
        elif id == 202:
            panel.copy_to_clipboard()
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 100, 'Zoom In')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 101, 'Zoom Out')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 200, 'Load')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 202, 'Copy to Clipboard')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
