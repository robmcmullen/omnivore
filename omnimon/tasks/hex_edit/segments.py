import sys
import wx

class SegmentList(wx.ListBox):
    """Segment selector for choosing which portion of the binary data to view
    """

    def __init__(self, parent, task, **kwargs):
        self.task = task
        
        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE|wx.SIMPLE_BORDER, **kwargs)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)

        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)
    
    def set_task(self, task):
        self.task = task
    
    def set_segments(self, segments, selected=0):
        items = [str(s) for s in segments]
        self.SetItems(items)
        self.SetSelection(selected)

    def on_click(self, event):
        selected = event.GetExtraLong()
        if selected:
            item = event.GetSelection()
            editor = self.task.active_editor
            print "Selected segment %d for document %s, control %s" % (item, editor.document, event.GetEventObject())
            wx.CallAfter(editor.view_segment_number, item)
        event.Skip()
    
    def on_dclick(self, event):
        event.Skip()
    
    def on_popup(self, event):
        event.Skip()
