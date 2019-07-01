import sys
import wx

from .actions import *

import logging
log = logging.getLogger(__name__)


class SegmentList(wx.ListBox):
    """Segment selector for choosing which portion of the binary data to view
    """

    def __init__(self, parent, linked_base, mdict, viewer_cls, **kwargs):
        self.linked_base = linked_base

        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE, **kwargs)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        self.Bind(wx.EVT_MOTION, self.on_tooltip)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        if sys.platform.startswith("linux") and not parent.IsTopLevel():
            # hack needed to force the main window to get Ctrl-F keystrokes. If
            # this ListBox is a direct child of a top-level frame, this is not
            # needed as it won't be visible all the time and therefore won't
            # interfere with the normal Ctrl-F find processing
            self.ui_action = wx.UIActionSimulator()
            self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook_find_hack)
        self.index_to_segment_uuid = []
        self.segment_uuid_to_index = {}

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

    def recalc_view(self):
        c = self.linked_base.document.collection
        self.set_segments(c, self.linked_base.segment_uuid)

    def refresh_view(self):
        self.Refresh()

    def show_segment_in_list(self, segment):
        return hasattr(segment, "container")

    def filter_segments(self, collection, selected=None):
        self.index_to_segment_uuid = []
        self.segment_uuid_to_index = {}
        names = []
        found = 0
        for segment_index, (segment, level) in enumerate(collection.iter_menu()):
            if self.show_segment_in_list(segment):
                if selected == segment.uuid:
                    found = len(self.index_to_segment_uuid)
                self.index_to_segment_uuid.append(segment.uuid)
                self.segment_uuid_to_index[segment.uuid] = len(names)
                names.append((level - 1) * "    " + str(segment))
        return names, found

    def set_segments(self, collection, selected=0):
        items, selected = self.filter_segments(collection, selected)
        if len(items) != self.GetCount():
            self.SetItems(items)
        else:
            for i, item in enumerate(items):
                old = self.GetString(i)
                if old != item:
                    self.SetString(i, item)
        self.SetSelection(selected)

    def on_char_hook_find_hack(self, evt):
        log.debug("on_char_hook_find_hack! char=%s, key=%s, modifiers=%s" % (evt.GetUnicodeKey(), evt.GetKeyCode(), bin(evt.GetModifiers())))
        if evt.GetUnicodeKey() == 70 and evt.ControlDown():
            log.debug("on_char_hook_find_hack! redirecting to %s" % self.linked_base.editor.control)
            # On linux/GTK, the ctrl-F is bound to the list's own find command,
            # which is useless for us. By redirecting it to the main window,
            # omnivore's find command can be called.
            wx.CallAfter(self.linked_base.editor.control.SetFocus)
            wx.CallAfter(self.ui_action.KeyDown, evt.GetKeyCode(),evt.GetModifiers())
            wx.CallAfter(self.ui_action.KeyUp, evt.GetKeyCode(),evt.GetModifiers())
        else:
            evt.Skip()

    def on_left_down(self, event):
        item = self.HitTest(event.GetPosition())
        if item >= 0:
            selected = self.GetSelection()
            if selected != item:
                self.process_segment_change(item)
        event.Skip()

    def on_click(self, event):
        # BUG: doesn't seem to get called when selecting a segment, using the
        # comments sidebar to jump to another segment, then attempting to
        # select that previous segment. This function never gets called in
        # that case, so I had to add the check on EVT_LEFT_DOWN
        selected = event.GetExtraLong()
        if selected:
            self.process_segment_change(event.GetSelection())
        event.Skip()

    def process_segment_change(self, index):
        segment_uuid = self.index_to_segment_uuid[index]
        if segment_uuid != self.linked_base.segment_uuid:
            wx.CallAfter(self.linked_base.view_segment_uuid, segment_uuid)

    def on_dclick(self, event):
        event.Skip()

    def on_popup(self, event):
        pos = event.GetPosition()
        selected = self.HitTest(pos)
        if selected == -1:
            event.Skip()
            return
        uuid = self.index_to_segment_uuid[selected]
        e = self.linked_base.editor
        # d = e.document

        # # include disabled action showing the name of the segment clicked upon
        # # because it may be different than the selected item
        # name = segment.name
        # if not name:
        #     name = str(segment)
        # actions = [
        #     Action(name=name, task=t, enabled=False),
        #     None,
        #     ]
        # if selected > 0:
        #     actions.append(SelectSegmentInAllAction(segment_uuid=uuid, task=t))
        #     actions.append(ParseSubSegmentsAction(segment_uuid=uuid, task=t))
        #     actions.append(SetSegmentOriginAction(segment_uuid=uuid, task=t))
        #     actions.append(DeleteUserSegmentAction(segment_uuid=uuid, task=t))
        #     actions.append(None)
        # savers = e.get_extra_segment_savers(segment)
        # savers.extend(segment.savers)
        # for saver in savers:
        #     action = SaveSegmentAsFormatAction(saver=saver, segment_uuid=selected, task=t, name="Save as %s" % saver.export_data_name)
        #     actions.append(action)
        # if actions:
        #     e.popup_context_menu_from_actions(self, actions)

    def on_tooltip(self, evt):
        pos = evt.GetPosition()
        selected = self.HitTest(pos)
        if selected >= 0:
            segment = self.linked_base.document.segments[selected]
            self.linked_base.editor.frame.status_message(segment.verbose_info)
        else:
            self.linked_base.editor.frame.status_message("")
        evt.Skip()

    def ensure_visible(self, segment):
        d = self.task.active_editor.document
        index = d.find_segment_index(segment)
        self.EnsureVisible(index)

    def on_key_down(self, evt):
        key = evt.GetKeyCode()
        log.debug("evt=%s, key=%s" % (evt, key))
        moved = False
        index = self.GetSelection()
        if key == wx.WXK_RETURN or key == wx.WXK_TAB:
            self.process_segment_change(index)
        elif key == wx.WXK_UP:
            index = max(index - 1, 0)
            moved = True
        elif key == wx.WXK_DOWN:
            index = min(index + 1, len(self.index_to_segment_uuid) - 1)
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
            self.process_segment_change(index)

    def on_key_up(self, evt):
        # Return key not sent through to EVT_CHAR, EVT_CHAR_HOOK or
        # EVT_KEY_DOWN events in a ListBox. This is the only event handler
        # that catches a Return.
        key = evt.GetKeyCode()
        log.debug("key down: %s" % key)
        index = self.GetSelection()
        if key == wx.WXK_RETURN:
            self.task.on_hide_minibuffer_or_cancel(evt)
        evt.Skip()

    def move_caret(self, segment_uuid):
        try:
            index = self.segment_uuid_to_index[segment_uuid]
        except KeyError:
            return
        self.SetSelection(index)
