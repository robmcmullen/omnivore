import sys
import time

import wx

from ..editor import get_editors


class PreferencesDialog(wx.Dialog):
    border = 3

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Preferences", size=(700, 400), pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self.book = wx.Treebook(self, -1, style=wx.LB_LEFT)
        sizer.Add(self.book, 1, wx.ALL|wx.EXPAND, self.border)

        self.add_pages()

        # self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGED, self.OnPageChanged)
        # self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGING, self.OnPageChanging)

        btnsizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.SetDefault()
        btnsizer.AddButton(self.ok_btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.ALL|wx.EXPAND, self.border)

        self.Bind(wx.EVT_BUTTON, self.on_button)

        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)

    def add_pages(self):
        editors = get_editors()
        for e in editors:
            print(e, e.preferences_module)
            panel = wx.Panel(self.book, -1, size=(500,500))
            text = wx.StaticText(panel, -1, f"{e.editor_id}: {e.preferences_module}")
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            sizer.Add(text, 0, wx.ALL|wx.EXPAND, self.border)
            self.book.AddPage(panel, e.ui_name)

    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.persist_preferences()
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def persist_preferences(self):
        print("STUFF!")
