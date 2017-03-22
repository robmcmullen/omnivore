import wx


class SelectionMixin(object):
    def __init__(self):
        self.multi_select_mode = False
        self.select_extend_mode = False
        self.mouse_drag_started = False

    def handle_select_start(self, editor, evt, selecting_rows=False, col=0):
        self.mouse_drag_started = True
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        if c < 0 or selecting_rows or not inside:
            c = 0
            selecting_rows = True
        else:
            selecting_rows = False
        if evt.ControlDown():
            self.multi_select_mode = True
            self.select_extend_mode = False
        elif evt.ShiftDown():
            self.multi_select_mode = False
            self.select_extend_mode = True
        if self.select_extend_mode:
            if index1 < editor.anchor_start_index:
                editor.anchor_start_index = index1
                editor.cursor_index = index1
            elif index2 > editor.anchor_start_index:
                editor.anchor_end_index = index2
                editor.cursor_index = index2 - 1
            editor.anchor_initial_start_index, editor.anchor_initial_end_index = editor.anchor_start_index, editor.anchor_end_index
            editor.select_range(editor.anchor_start_index, editor.anchor_end_index, add=self.multi_select_mode)
        else:
            self.ClearSelection()
            if selecting_rows:
                index1, index2 = self.get_start_end_index_of_row(r)
            editor.anchor_initial_start_index, editor.anchor_initial_end_index = index1, index2
            editor.cursor_index = index1
            if not selecting_rows:
                # initial click when not selecting rows should move the cursor,
                # not select the grid square
                index2 = index1
            editor.select_range(index1, index2, add=self.multi_select_mode)
        wx.CallAfter(editor.index_clicked, editor.cursor_index, c, self, True)

    def handle_select_motion(self, editor, evt, selecting_rows=False):
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        if c < 0 or selecting_rows or not inside:
            selecting_rows = True
            c = 0
        else:
            selecting_rows = False
        update = False
        if self.select_extend_mode:
            if index1 < editor.anchor_initial_start_index:
                editor.select_range(index1, editor.anchor_initial_end_index, extend=True)
                update = True
            else:
                editor.select_range(editor.anchor_initial_start_index, index2, extend=True)
                update = True
        else:
            if editor.anchor_start_index <= index1:
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index2 != editor.anchor_end_index:
                    editor.select_range(editor.anchor_initial_start_index, index2, extend=self.multi_select_mode)
                    update = True
            else:
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index1 != editor.anchor_end_index:
                    editor.select_range(editor.anchor_initial_end_index, index1, extend=self.multi_select_mode)
                    update = True
        if update:
            editor.cursor_index = index1
            wx.CallAfter(editor.index_clicked, editor.cursor_index, c, self, True)

    def handle_select_end(self, editor, evt):
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False

    def ClearSelection(self):
        # Stub function for those controls that don't have it. Tables use this
        # but nothing else so far.
        pass

    def get_location_from_event(self, evt):
        raise NotImplementedError

    def get_start_end_index_of_row(self, row):
        raise NotImplementedError
