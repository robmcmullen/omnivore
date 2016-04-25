import wx

from omnivore.framework.panes import FrameworkPane

# Enthought library imports.
from pyface.api import YES, NO

# Local imports.
from disassembly import DisassemblyPanel
from segments import SegmentList
from omnivore.utils.wx.bitviewscroller import BitmapScroller, FontMapScroller, MemoryMapScroller
from omnivore.utils.wx.springtabs import SpringTabs
from omnivore.framework.undo_panel import UndoHistoryPanel
from commands import ChangeByteCommand

import logging
log = logging.getLogger(__name__)


class MemoryMapSpringTab(MemoryMapScroller):
    def activateSpringTab(self):
        self.recalc_view()

class CommentsPanel(wx.VListBox):
    def __init__(self, parent, task, **kwargs):
        self.task = task
        self.editor = None
        self.items = []
        wx.VListBox.__init__(self, parent, wx.ID_ANY, **kwargs)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        
        f = self.GetFont()
        self.bold_font = wx.Font(f.GetPointSize(), f.GetFamily(),
                                 f.GetStyle(), wx.BOLD, f.GetUnderlined(),
                                 f.GetFaceName(), f.GetEncoding())
        self.italic_font = wx.Font(f.GetPointSize(), f.GetFamily(),
                                   wx.FONTSTYLE_ITALIC, wx.NORMAL, f.GetUnderlined(),
                                   f.GetFaceName(), f.GetEncoding())
        
        # Return key not sent through to EVT_CHAR, EVT_CHAR_HOOK or
        # EVT_KEY_DOWN events in a ListBox. This is the only event handler
        # that catches a Return.
        self.Bind(wx.EVT_KEY_UP, self.on_char)

    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        item = self.items[n]
        dc.SetFont(item[3])
        dc.SetTextForeground(c)
        dc.DrawLabel(item[2], rect,
                     wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        height = 0
        text = self.items[n][2]
        for line in text.split('\n'):
            w, h = self.GetTextExtent(line)
            height += h
        return height + 2

    def DoGetBestSize(self):
        """ Base class virtual method for sizer use to get the best size
        """
        width = 500
        height = -1
        best = wx.Size(width, height)

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best
    
    def on_char(self, evt):
        keycode = evt.GetKeyCode()
        log.debug("key down: %s" % keycode)
        if keycode == wx.WXK_RETURN:
            index = self.GetSelection()
            self.process_index(index)
        evt.Skip()

    def on_click(self, evt):
        index = self.HitTest(evt.GetPosition())
        if index >= 0:
            self.SetSelection(index)
            self.process_index(index)
            self.set_items()
            self.Refresh()
    
    def process_index(self, index):
        e = self.editor
        segment, index, text, font = self.items[index]
        if segment == self.editor.segment:
            e.index_clicked(index, 0, None)
        else:
            n = e.document.find_segment_index(segment)
            e.view_segment_number(n)
            e.index_clicked(index, 0, None)
    
    def set_items(self, items=None):
        if items is None:
            items = self.input_items
        self.input_items = items
        seen = set()
        self.items = []
        for i in items:
            self.process_comment(i, seen)
        self.SetItemCount(len(self.items))
    
    def process_comment(self, item, segment_seen):
        e = self.editor
        try:
            segment = e.segment
            if segment == e.document.segments[0]:
                # if we're currently in the main segment, check for the index
                # in user segments first, rather than listing everything in
                # the main segment.
                raise IndexError
            index = segment.get_index_from_base_index(item[0])
            label = e.get_label_at_index(index)
            font = self.GetFont()
            segment_font = self.bold_font
        except IndexError:
            font = self.italic_font
            segment_font = self.italic_font
            segment, index = e.find_in_user_segment(item[0])
            if segment is not None:
                label = segment.label(index)
            else:
                index = item[0]
                label = "%04x" % index
        if segment not in segment_seen:
            segment_seen.add(segment)
            self.items.append((segment, 0, str(segment), segment_font))
        self.items.append((segment, index, "  %s: %s" % (label, item[1]), font))

    def recalc_view(self):
        e = self.task.active_editor
        self.editor = e
        if e is not None:
            self.set_items(e.document.segments[0].get_sorted_comments())
    
    def refresh_view(self):
        editor = self.task.active_editor
        if editor is not None:
            if self.editor != editor:
                self.recalc_view()
            else:
                self.Refresh()
        
    def activateSpringTab(self):
        self.recalc_view()
    
    def get_notification_count(self):
        self.recalc_view()
        return len(self.items)

class SidebarPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.sidebar'
    name = 'Sidebar'
    
    movable = False
    caption_visible = False
    dock_layer = 9
    
    def MemoryMapCB(self, parent, task, **kwargs):
        control = MemoryMapSpringTab(parent, task)
    
    def comments_cb(self, parent, task, **kwargs):
        control = CommentsPanel(parent, task)
        
    def create_contents(self, parent):
        control = SpringTabs(parent, self.task, popup_direction="left")
        control.addTab("Page Map", self.MemoryMapCB)
        control.addTab("Comments", self.comments_cb)
        return control
    
    def refresh_active(self):
        active = self.control._radio
        if active is not None and active.is_shown:
            active.managed_window.refresh_view()


class DisassemblyPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.disassembly'
    name = 'Disassembly'
    
    def create_contents(self, parent):
        control = DisassemblyPanel(parent, self.task, size=(300,500))
        return control


class BitmapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.bitmap'
    name = 'Bitmap'
    
    def create_contents(self, parent):
        control = BitmapScroller(parent, self.task, size=(64,500))
        return control


class FontMapPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.font_map'
    name = 'Char Map'
    
    def create_contents(self, parent):
        control = FontMapScroller(parent, self.task, size=(160,500), command=ChangeByteCommand)
        return control


class SegmentsPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.segments'
    name = 'Segments'
    
    def create_contents(self, parent):
        control = SegmentList(parent, self.task, size=(64,150))
        return control


class UndoPane(FrameworkPane):
    #### TaskPane interface ###################################################

    id = 'hex_edit.undo'
    name = 'Undo History'
    
    def create_contents(self, parent):
        control = UndoHistoryPanel(parent, self.task, size=(64,150))
        return control
