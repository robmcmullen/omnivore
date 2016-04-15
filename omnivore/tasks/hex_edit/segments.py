import sys
import wx

from pyface.action.api import Action, ActionItem, Separator

from actions import *

class SegmentList(wx.ListBox):
    """Segment selector for choosing which portion of the binary data to view
    """

    def __init__(self, parent, task, **kwargs):
        self.task = task
        
        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE, **kwargs)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        self.Bind(wx.EVT_MOTION, self.on_tooltip)
    
    def set_task(self, task):
        self.task = task
    
    def set_segments(self, segments, selected=0):
        items = [str(s) for s in segments]
        if len(items) != self.GetCount():
            self.SetItems(items)
        else:
            for i, item in enumerate(items):
                old = self.GetString(i)
                if old != item:
                    self.SetString(i, item)
        self.SetSelection(selected)

    def on_click(self, event):
        selected = event.GetExtraLong()
        if selected:
            item = event.GetSelection()
            editor = self.task.active_editor
            wx.CallAfter(editor.view_segment_number, item)
        event.Skip()
    
    def on_dclick(self, event):
        event.Skip()
    
    def on_popup(self, event):
        pos = event.GetPosition()
        selected = self.HitTest(pos)
        if selected == -1:
            event.Skip()
            return
        d = self.task.active_editor.document
        segment = d.segments[selected]
        
        # include disabled action showing the name of the segment clicked upon
        # because it may be different than the selected item
        name = segment.name
        if not name:
            name = str(segment)
        actions = [
            Action(name=name, task=self.task, enabled=False),
            None,
            ]
        if selected > 0:
            actions.append(SelectSegmentInAllAction(segment_number=selected, task=self.task))
            if d.is_user_segment(segment):
                actions.append(SetSegmentOriginAction(segment_number=selected, task=self.task))
                actions.append(DeleteUserSegmentAction(segment_number=selected, task=self.task))
            actions.append(None)
        for saver in segment.savers:
            action = SaveSegmentAsFormatAction(saver=saver, segment_number=selected, task=self.task, name="Save as %s" % saver.name)
            actions.append(action)
        if actions:
            self.task.active_editor.popup_context_menu_from_actions(self, actions)
    
    def on_tooltip(self, evt):
        pos = evt.GetPosition()
        selected = self.HitTest(pos)
        if selected >= 0:
            segment = self.task.active_editor.document.segments[selected]
            self.task.status_bar.message = segment.verbose_info
        else:
            self.task.status_bar.message = ""
        evt.Skip()
    
    def ensure_visible(self, segment):
        d = self.task.active_editor.document
        index = d.find_segment_index(segment)
        self.EnsureVisible(index)
