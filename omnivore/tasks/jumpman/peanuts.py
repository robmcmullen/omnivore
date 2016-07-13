import sys
import wx

import logging
log = logging.getLogger(__name__)

class TriggerList(wx.ListBox):
    """Trigger selector for choosing which trigger actions to edit
    """

    def __init__(self, parent, task, **kwargs):
        self.task = task
        self.triggers = None
        
        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE, **kwargs)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_MOTION, self.on_tooltip)
    
    def set_task(self, task):
        self.task = task
     
    def recalc_view(self):
        self.editor = e = self.task.active_editor
        if e is not None:
            selected = e.bitmap.trigger_root
            self.set_peanuts(selected)
    
    def refresh_view(self):
        e = self.editor
        if e is not None:
            if self.IsShown():
                log.debug("refreshing %s" % self)
                self.recalc_view()
            else:
                log.debug("skipping refresh of hidden %s" % self)
   
    def parse_peanuts(self, peanuts, items, triggers, indent=""):
        for peanut in peanuts:
            items.append(indent + peanut.trigger_str)
            triggers.append(peanut)
            children = []
            for p in peanut.trigger_painting:
                if p.single:
                    children.append(p)
            if children:
                self.parse_peanuts(children, items, triggers, indent + "    ")

    def set_peanuts(self, selected=None):
        items = ["Main Level"]
        triggers = [None]
        index = 1
        selected_index = 0
        state = self.editor.bitmap.screen_state
        if state is not None:
            self.parse_peanuts(state.sorted_peanuts, items, triggers)
            for index, trigger in enumerate(triggers):
                if trigger == selected:
                    selected_index = index
        if len(items) != self.GetCount():
            self.SetItems(items)
        else:
            for i, item in enumerate(items):
                old = self.GetString(i)
                if old != item:
                    self.SetString(i, item)
        if selected_index < self.GetCount():
            self.SetSelection(selected_index)
        self.triggers = triggers

    def on_left_down(self, event):
        item = self.HitTest(event.GetPosition())
        if item >= 0:
            selected = self.GetSelection()
            if selected != item:
                e = self.editor
                wx.CallAfter(e.set_trigger_view, self.triggers[item])
        event.Skip()

    def on_click(self, event):
        # BUG: doesn't seem to get called when selecting a segment, using the
        # comments sidebar to jump to another segment, then attempting to
        # select that previous segment. This function never gets called in
        # that case, so I had to add the check on EVT_LEFT_DOWN
        is_selected = event.GetExtraLong()
        if is_selected:
            selected = event.GetSelection()
            e = self.editor
            wx.CallAfter(e.set_trigger_view, self.triggers[selected])
        event.Skip()
    
    def on_dclick(self, event):
        event.Skip()
    
    def on_tooltip(self, evt):
        pos = evt.GetPosition()
        selected = self.HitTest(pos)
        if selected >= 0:
            self.task.status_bar.message = "peanut #%d" % selected
        else:
            self.task.status_bar.message = ""
        evt.Skip()
