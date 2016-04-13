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

class CommentsPanel(wx.ListBox):
    def __init__(self, parent, task, **kwargs):
        self.task = task
        self.editor = None
        self.items = []
        wx.ListBox.__init__(self, parent, wx.ID_ANY, **kwargs)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        
        # Return key not sent through to EVT_CHAR, EVT_CHAR_HOOK or
        # EVT_KEY_DOWN events in a ListBox. This is the only event handler
        # that catches a Return.
        self.Bind(wx.EVT_KEY_UP, self.on_char)

    def DoGetBestSize(self):
        """ Base class virtual method for sizer use to get the best size
        """
        width = 300
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
            self.Select(index)
            self.process_index(index)
    
    def process_index(self, index):
        e = self.editor
        item = self.items[index]
        print "Selected item", item
        inside = False
        try:
            index = e.segment.get_index_from_base_index(item[0])
            if e.segment.is_valid_index(index):
                inside = True
        except IndexError:
            pass
        if inside:
            e.index_clicked(index, 0, None)
        else:
            if e.task.confirm("Comment not in this segment.\n\nShow in main segment?", "View Comment") == YES:
                e.view_segment_number(0)
                e.index_clicked(item[0], 0, None)
    
    def set_items(self, items):
        self.items = list(items)
        self.Set([self.get_item_text(i) for i in items])
    
    def get_item_text(self, item):
        try:
            index = self.editor.segment.get_index_from_base_index(item[0])
            if self.editor.segment.is_valid_index(index):
                label = self.editor.get_label_at_index(index)
            else:
                label = "(%s in main)" % item[0]
        except IndexError:
            label = "(%s in main)" % item[0]
        return "%s: %s" % (label, item[1])

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
