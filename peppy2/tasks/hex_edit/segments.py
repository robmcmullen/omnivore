import sys
import wx

class SegmentList(wx.ListBox):
    """Segment selector for choosing which portion of the binary data to view
    """

    def __init__(self, parent, task):
        self.task = task
        
        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE|wx.SIMPLE_BORDER)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)

        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)
    
    def set_task(self, task):
        self.task = task
    
    def set_segments(self, segments):
        items = [str(s) for s in segments]
        self.SetItems(items)

    def on_click(self, event):
        item = event.GetSelection()
        print "Selected segment %d" % item
        event.Skip()
    
    def on_dclick(self, event):
        event.Skip()
    
    def on_popup(self, event):
        event.Skip()
