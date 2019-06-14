import os
import sys
from collections import namedtuple

import wx

from sawx.ui.undo_panel import UndoHistoryPanel
from ..editors.linked_base import VirtualTableLinkedBase
from .segments import SegmentList
from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)



class BaseInfoViewer(SegmentViewer):
    viewer_category = "Info"

    def use_default_view_params(self):
        pass

    def restore_view_params(self, params):
        pass

    def update_toolbar(self):
        pass

    def sync_caret(self, flags):
        pass

    def ensure_visible(self, flags):
        pass

    def recalc_data_model(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def recalc_view(self):
        self.control.recalc_view()
        self.control.refresh_view()

    def get_notification_count(self):
        return 0


class NonCaretInfoViewer(BaseInfoViewer):
    has_caret = False


class VirtualTableInfoViewer(BaseInfoViewer):
    """Info viewer for data that based on data from the segment but doesn't
    display the actual bytes segment in any one-to-one manner. This decouples
    the caret locations so clicking here won't move the cursor in other views.
    """

    @classmethod
    def replace_linked_base(cls, linked_base):
        # the new linked base decouples the cursor here from the other segments
        return VirtualTableLinkedBase(editor=linked_base.editor, segment=linked_base.segment)

    def create_post(self):
        self.linked_base.table = self.control.table

    # override caret display to not respond to caret move requests from other
    # viewers
    def show_caret(self, control, index, bit):
        pass


CommentItem = namedtuple('CommentItem', ('segment', 'index', 'label', 'font', 'type'))

class CommentsPanel(wx.VListBox):
    SEGMENT_TITLE = 0
    COMMENT_ENTRY = 1

    def __init__(self, parent, **kwargs):
        self.items = []
        wx.VListBox.__init__(self, parent, wx.ID_ANY, **kwargs)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)

        f = self.GetFont()
        self.normal_font = f
        self.bold_font = wx.Font(f.GetPointSize(), f.GetFamily(),
                                 f.GetStyle(), wx.BOLD, f.GetUnderlined(),
                                 f.GetFaceName(), f.GetEncoding())
        self.italic_font = wx.Font(f.GetPointSize(), f.GetFamily(),
                                   wx.FONTSTYLE_ITALIC, wx.NORMAL, f.GetUnderlined(),
                                   f.GetFaceName(), f.GetEncoding())
        _, self.font_height = self.GetTextExtent("MWSqj")
        self.select_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        self.select_bg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        self.select_brush = wx.Brush(self.select_bg_color, wx.SOLID)
        self.normal_color = self.GetForegroundColour()
        self.SetBackgroundColour(wx.GREEN)

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        # Return key not sent through to EVT_CHAR, EVT_CHAR_HOOK or
        # EVT_KEY_DOWN events in a ListBox. This is the only event handler
        # that catches a Return.
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.last_segment = None

    def on_erase_background(self, evt):
        """Windows flickers like crazy when erasing the whole screen, so just
        erase the parts that won't be filled in later.
        """
        dc = evt.GetDC()
        w, h = self.GetClientSize()
        print(("erasing background", w, h))
        dc.SetBrush(self.select_brush)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, w, h)

    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            dc.SetTextForeground(self.select_color)
        else:
            dc.SetTextForeground(self.normal_color)
        item = self.items[n]
        dc.SetFont(item.font)
        dc.DrawLabel(item.label, rect,
                     wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    def OnDrawBackground(self, dc, rect, n):
        if self.GetSelection() == n:
            dc.SetBrush(self.select_brush)
        else:
            dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(rect)

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
        #     index = self.table.get_page_index(e.caret_index, e.segment.page_size, -1, self)
        #     moved = True
        # elif key == wx.WXK_PAGEDOWN:
        #     index = self.table.get_page_index(e.caret_index, e.segment.page_size, 1, self)
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
            pass
        evt.Skip()

    def on_click(self, evt):
        index = self.HitTest(evt.GetPosition())
        if index >= 0:
            self.SetSelection(index)
            self.process_index(index)
            self.Refresh()
        evt.Skip()

    def process_index(self, index):
        v = self.segment_viewer
        item = self.items[index]
        if item.segment == v.segment:
            v.linked_base.sync_caret_to_index(item.index)
        else:
            v.linked_base.find_segment(item.segment)
            v.linked_base.sync_caret_to_index(item.index)
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
        font = self.normal_font
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
        v = self.segment_viewer
        segment = v.segment
        try:
            if segment == v.document.segments[0]:
                # if we're currently in the main segment, check for the index
                # in user segments first, rather than listing everything in
                # the main segment.
                raise IndexError
            index = segment.reverse_offset[item[0]]
            if index < 0:
                raise IndexError
            label = segment.address(index)
            font = self.normal_font
            segment_font = self.bold_font
        except IndexError:
            font = self.italic_font
            segment_font = self.italic_font
            # segment, index = v.editor.find_in_user_segment(item[0])
            segment = None
            if segment is not None:
                label = segment.address(index)
            else:
                index = item[0]
                label = "%04x" % index
        show = False
        if segment is None and segment not in segment_seen:
            segment_seen.add(segment)
            show = True
        elif segment is not None and segment.uuid not in segment_seen:
            segment_seen.add(segment.uuid)
            show = True
        if show:
            self.items.append(CommentItem._make((segment, 0, str(segment), segment_font, self.SEGMENT_TITLE)))
        self.items.append(CommentItem._make((segment, index, "  %s: %s" % (label, item[1]), font, self.COMMENT_ENTRY)))

    def recalc_view(self):
        v = self.segment_viewer
        segment = v.segment
        try:
            container = v.segment.container
        except AttributeError:
            comments = []
        else:
            comments = container.get_sorted_comments()
        # print(("COMMENTS!", str(comments)))
        self.set_items(comments)

    def refresh_view(self):
        self.Refresh()


class CommentsViewer(NonCaretInfoViewer):
    name = "comments"

    ui_name = "Comments"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return CommentsPanel(parent, size=(100,500))

    def show_caret(self, control, index, bit):
        pass

    ##### Spring Tab interface

    def get_notification_count(self):
        self.control.recalc_view()
        return len(self.control.items)


class UndoViewer(NonCaretInfoViewer):
    name = "undo"

    ui_name = "Undo History"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return UndoHistoryPanel(parent, linked_base.editor, size=(100,500))

    def show_caret(self, control, index, bit):
        self.control.recalc_view()
        self.control.refresh_view()

    def refresh_view(self, flags):
        self.recalc_view()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class SegmentListViewer(NonCaretInfoViewer):
    name = "segments"

    ui_name = "Segments"

    control_cls = SegmentList

    def recalc_data_model(self):
        pass

    def show_caret(self, control, index, bit):
        pass

    # @on_trait_change('linked_base.editor.document.segments_changed')
    def process_segments_changed(self, evt):
        log.debug("process_segments_changed for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.set_segments(self.linked_base.editor.document.segments, self.linked_base.segment_uuid)
            self.recalc_view()

    # # @on_trait_change('linked_base.segment_selected')
    # def process_segment_selected(self, evt):
    #     log.debug("process_segment_selected for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
    #     if evt is not Undefined:
    #         self.control.move_caret(evt)  # evt is segment number

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0
