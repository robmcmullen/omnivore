import os
import sys
from collections import namedtuple

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.framework.undo_panel import UndoHistoryPanel
from omnivore8bit.byte_edit.segments import SegmentList
from . import SegmentViewer

import logging
log = logging.getLogger(__name__)



class BaseInfoViewer(SegmentViewer):
    has_metadata_only = True


CommentItem = namedtuple('CommentItem', ('segment', 'index', 'label', 'font', 'type'))

class CommentsPanel(wx.VListBox):
    SEGMENT_TITLE = 0
    COMMENT_ENTRY = 1

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
        _, self.font_height = self.GetTextExtent("MWSqj")
        self.select_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        self.normal_color = self.GetForegroundColour()

        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        # Return key not sent through to EVT_CHAR, EVT_CHAR_HOOK or
        # EVT_KEY_DOWN events in a ListBox. This is the only event handler
        # that catches a Return.
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)

        self.last_segment = None

    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = self.select_color
        else:
            c = self.normal_color
        item = self.items[n]
        dc.SetFont(item.font)
        dc.SetTextForeground(c)
        dc.DrawLabel(item.label, rect,
                     wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        height = 0
        text = self.items[n].label
        for line in text.split('\n'):
            height += self.font_height
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

    def on_key_down(self, evt):
        key = evt.GetKeyCode()
        log.debug("evt=%s, key=%s" % (evt, key))
        moved = False
        index = self.GetSelection()
        if key == wx.WXK_TAB:
            self.process_index(index)
        elif key == wx.WXK_UP:
            index = max(index - 1, 0)
            moved = True
        elif key == wx.WXK_DOWN:
            index = min(index + 1, len(self.items) - 1)
            moved = True
        # elif key == wx.WXK_PAGEUP:
        #     index = self.table.get_page_index(e.cursor_index, e.segment.page_size, -1, self)
        #     moved = True
        # elif key == wx.WXK_PAGEDOWN:
        #     index = self.table.get_page_index(e.cursor_index, e.segment.page_size, 1, self)
        #     moved = True
        else:
            evt.Skip()
        # if True:
        #     evt.Skip()
        #     return
        if moved:
            self.SetSelection(index)
            self.process_index(index)
            self.Refresh()

    def on_key_up(self, evt):
        keycode = evt.GetKeyCode()
        log.debug("key up: %s" % keycode)
        if keycode == wx.WXK_RETURN:
            self.task.on_hide_minibuffer_or_cancel(evt)
        evt.Skip()

    def on_click(self, evt):
        index = self.HitTest(evt.GetPosition())
        if index >= 0:
            self.SetSelection(index)
            self.process_index(index)
            self.Refresh()
        evt.Skip()

    def process_index(self, index):
        e = self.editor
        item = self.items[index]
        if item.segment == self.editor.segment:
            e.index_clicked(item.index, 0, None)
        else:
            n = e.document.find_segment_index(item.segment)
            e.view_segment_number(n)
            e.index_clicked(item.index, 0, None)
        if item.segment != self.last_segment:
            self.update_items(item.segment)

    def set_items(self, items=None):
        if items is None:
            items = self.input_items
        self.input_items = items
        seen = set()
        self.items = []
        for i in items:
            self.process_comment(i, seen)
        self.SetItemCount(len(self.items))

    def update_items(self, segment):
        self.last_segment = segment
        new_items = []
        font = self.GetFont()
        for item in self.items:
            new_item = item
            if item.segment == segment:
                if item.type == self.SEGMENT_TITLE:
                    new_item = item._replace(font=self.bold_font)
                else:
                    new_item = item._replace(font=font)
            else:
                new_item = item._replace(font=self.italic_font)
            new_items.append(new_item)
        self.items = new_items

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
            self.items.append(CommentItem._make((segment, 0, str(segment), segment_font, self.SEGMENT_TITLE)))
        self.items.append(CommentItem._make((segment, index, "  %s: %s" % (label, item[1]), font, self.COMMENT_ENTRY)))

    def recalc_view(self):
        e = self.task.active_editor
        self.editor = e
        if e is not None:
            self.set_items(e.document.segments[0].get_sorted_comments())

    def refresh_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.Refresh()


class CommentsViewer(BaseInfoViewer):
    name = "comments"

    pretty_name = "Comments"

    @classmethod
    def create_control(cls, parent, linked_base):
        return CommentsPanel(parent, linked_base.editor.task, size=(100,500))

    def recalc_data_model(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def recalc_view(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def show_cursor(self, control, index, bit):
        pass

    ##### Spring Tab interface

    def get_notification_count(self):
        self.control.recalc_view()
        return len(self.control.items)


class UndoViewer(BaseInfoViewer):
    name = "undo"

    pretty_name = "Undo History"

    @classmethod
    def create_control(cls, parent, linked_base):
        return UndoHistoryPanel(parent, linked_base.editor.task, size=(100,500))

    def recalc_data_model(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def recalc_view(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def show_cursor(self, control, index, bit):
        self.control.recalc_view()
        self.control.refresh_view()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class SegmentListViewer(BaseInfoViewer):
    name = "segments"

    pretty_name = "Segments"

    @classmethod
    def create_control(cls, parent, linked_base):
        return SegmentList(parent, linked_base.editor.task, size=(100,500))

    def recalc_data_model(self):
        pass

    def show_cursor(self, control, index, bit):
        pass

    @on_trait_change('linked_base.editor.task.segments_changed')
    def process_segments_changed(self, evt):
        log.debug("process_segments_changed for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.set_segments(self.linked_base.editor.document.segments, self.linked_base.segment_number)
            self.recalc_view()

    @on_trait_change('linked_base.editor.task.segment_selected')
    def process_segment_selected(self, evt):
        log.debug("process_segment_selected for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.move_cursor(evt)  # evt is segment number

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0
