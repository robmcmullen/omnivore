import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger(__name__)


class RawStatusBar(wx.StatusBar):
    gripper_unusable_width = 15  # extra space on right side so gripper doesn't get drawn over text

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)

        self.Bind(wx.EVT_SIZE, self.on_size)

        self.default_field = 0
        self.debug_field = 0

    def on_size(self, evt):
        wx.CallAfter(self.reposition_controls)
        evt.Skip()

    def reposition_controls(self):
        """Any child controls must be repositioned manually since there is no
        sizer to manage things.

        To maximize the size of the control in each field, use e.g.:

            rect = self.GetFieldRect(i)
            rect.x += 1
            rect.y += 1
            self.child_control[i].SetRect(rect)
        """
        pass

    def message(self, text):
        self.SetStatusText(text, self.default_field)

    def debug(self, text):
        self.SetStatusText(text, self.debug_field)


class StatusbarDescription:
    def __init__(self, parent, editor):
        self.fields = editor.statusbar_desc

    def sync_with_editor(self, statusbar_control):
        widths = [field[1] for field in self.fields]
        widths.append(statusbar_control.gripper_unusable_width)
        statusbar_control.SetFieldsCount(len(widths), widths)
        statusbar_control.default_field = 0
        statusbar_control.debug_field = 0
        for i, (name, width) in enumerate(self.fields):
            if name == "debug":
                statusbar_control.debug_field = i
