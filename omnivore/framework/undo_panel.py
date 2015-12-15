#!/usr/bin/env python

import sys
import traceback
import wx


class UndoHistoryPanel(wx.Panel):
    def __init__(self, parent, task, **kwargs):
        self.task = task
        wx.Panel.__init__(self, parent, wx.ID_ANY, **kwargs)
        
        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.history = wx.ListBox(self, size=(100, -1))

        self.sizer.Add(self.history, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.sizer.Layout()
        self.Fit()
    
    def set_task(self, task):
        self.task = task

    def update_history(self):
        project = self.task.active_editor
        summary = project.document.undo_stack.history_list()
        self.history.Set(summary)
        index = project.document.undo_stack.insert_index
        if index > 0:
            self.history.SetSelection(index - 1)
