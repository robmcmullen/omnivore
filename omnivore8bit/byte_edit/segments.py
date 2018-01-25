import sys
import wx

from pyface.action.api import Action, ActionItem, Separator

from actions import *

import logging
log = logging.getLogger(__name__)


class SegmentList(wx.ListBox):
    """Segment selector for choosing which portion of the binary data to view
    """

    def __init__(self, parent, task, **kwargs):
        self.task = task

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
        self.index_to_segment_number = []
        self.segment_number_to_index = {}

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

    def set_task(self, task):
        self.task = task

    def recalc_view(self):
        e = self.task.active_editor
        self.editor = e
        if e is not None:
            self.set_segments(e.document.segments, e.segment_number)

    def refresh_view(self):
        editor = self.task.active_editor
        if editor is not None:
            if self.editor != editor:
                self.recalc_view()
            else:
                self.Refresh()

    def show_segment_in_list(self, segment):
        return True

    def filter_segments(self, segments, selected=0):
        self.index_to_segment_number = []
        self.segment_number_to_index = {}
        names = []
        found = 0
        for segment_index, s in enumerate(segments):
            if self.show_segment_in_list(s):
                if selected == segment_index:
                    found = len(self.index_to_segment_number)
                self.index_to_segment_number.append(segment_index)
                self.segment_number_to_index[segment_index] = len(names)
                names.append(str(s))
        return names, found

    def set_segments(self, segments, selected=0):
        items, selected = self.filter_segments(segments, selected)
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
            log.debug("on_char_hook_find_hack! redirecting to %s" % self.task.active_editor.control)
            # On linux/GTK, the ctrl-F is bound to the list's own find command,
            # which is useless for us. By redirecting it to the main window,
            # omnivore's find command can be called.
            wx.CallAfter(self.task.active_editor.control.SetFocus)
            wx.CallAfter(self.ui_action.KeyDown, evt.GetKeyCode(),evt.GetModifiers())
            wx.CallAfter(self.ui_action.KeyUp, evt.GetKeyCode(),evt.GetModifiers())
        else:
            evt.Skip()

    def on_left_down(self, event):
        item = self.HitTest(event.GetPosition())
        if item >= 0:
            selected = self.GetSelection()
            if selected != item:
                editor = self.task.active_editor
                segment_number = self.index_to_segment_number[item]
                wx.CallAfter(editor.view_segment_number, segment_number)
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
        editor = self.task.active_editor
        segment_number = self.index_to_segment_number[index]
        if segment_number != editor.segment_number:
            wx.CallAfter(editor.view_segment_number, segment_number)

    def on_dclick(self, event):
        event.Skip()

    def on_popup(self, event):
        pos = event.GetPosition()
        selected = self.HitTest(pos)
        if selected == -1:
            event.Skip()
            return
        e = self.task.active_editor
        d = e.document
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
            actions.append(ParseSubSegmentsAction(segment_number=selected, task=self.task))
            if segment != d.container_segment:
                actions.append(SetSegmentOriginAction(segment_number=selected, task=self.task))
                actions.append(DeleteUserSegmentAction(segment_number=selected, task=self.task))
            actions.append(None)
        savers = e.get_extra_segment_savers(segment)
        savers.extend(segment.savers)
        for saver in savers:
            action = SaveSegmentAsFormatAction(saver=saver, segment_number=selected, task=self.task, name="Save as %s" % saver.export_data_name)
            actions.append(action)
        if actions:
            e.popup_context_menu_from_actions(self, actions)

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
            index = min(index + 1, len(self.index_to_segment_number) - 1)
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

    def move_caret(self, segment_number):
        try:
            index = self.segment_number_to_index[segment_number]
        except KeyError:
            return
        self.SetSelection(index)
