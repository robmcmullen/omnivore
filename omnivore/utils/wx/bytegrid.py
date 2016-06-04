import sys
import wx

import wx.grid as Grid

from atrcopy import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask, diff_bit_mask

import logging
log = logging.getLogger(__name__)


class ByteGridRenderer(Grid.PyGridCellRenderer):
    def __init__(self, table, editor):
        """Render data in the specified color and font and fontsize"""
        Grid.PyGridCellRenderer.__init__(self)
        self.table = table
        m = editor.machine
        self.color = m.text_color
        self.diff_color = m.diff_text_color
        self.font = m.text_font
        self.selected_background = m.highlight_color
        self.selected_brush = wx.Brush(m.highlight_color, wx.SOLID)
        self.selected_pen = wx.Pen(m.highlight_color, 1, wx.SOLID)
        self.normal_background = m.background_color
        self.normal_brush = wx.Brush(m.background_color, wx.SOLID)
        self.normal_pen = wx.Pen(m.background_color, 1, wx.SOLID)
        self.data_background = m.data_color
        self.data_brush = wx.Brush(m.data_color, wx.SOLID)
        self.cursor_background = m.background_color
        self.cursor_brush = wx.Brush(m.background_color, wx.TRANSPARENT)
        self.cursor_pen = wx.Pen(m.unfocused_cursor_color, 2, wx.SOLID)
        self.match_background = m.match_background_color
        self.match_brush = wx.Brush(m.match_background_color, wx.SOLID)
        self.match_pen = wx.Pen(m.match_background_color, 1, wx.SOLID)
        self.comment_background = m.comment_background_color
        self.comment_brush = wx.Brush(m.comment_background_color, wx.SOLID)
        self.comment_pen = wx.Pen(m.comment_background_color, 1, wx.SOLID)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        # Here we draw text in a grid cell using various fonts
        # and colors.  We have to set the clipping region on
        # the grid's DC, otherwise the text will spill over
        # to the next cell
        dc.SetClippingRect(rect)

        # clear the background
        dc.SetBackgroundMode(wx.SOLID)
        
        index, _ = self.table.get_index_range(row, col)
        if not self.table.is_index_valid(index):
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
            dc.DrawRectangleRect(rect)
        else:
            text, style = self.table.get_value_style(row, col)
            style = self.table.get_style_override(row, col, style)
            if style & selected_bit_mask:
                dc.SetPen(self.selected_pen)
                dc.SetBrush(self.selected_brush)
                dc.SetTextBackground(self.selected_background)
            elif style & match_bit_mask:
                dc.SetPen(self.match_pen)
                dc.SetBrush(self.match_brush)
                dc.SetTextBackground(self.match_background)
            elif style & comment_bit_mask:
                dc.SetPen(self.comment_pen)
                dc.SetBrush(self.comment_brush)
                dc.SetTextBackground(self.comment_background)
            elif style & data_bit_mask:
                dc.SetPen(self.normal_pen)
                dc.SetBrush(self.data_brush)
                dc.SetTextBackground(self.data_background)
            else:
                dc.SetPen(self.normal_pen)
                dc.SetBrush(self.normal_brush)
                dc.SetTextBackground(self.normal_background)
            dc.DrawRectangleRect(rect)

            dc.SetBackgroundMode(wx.SOLID)

            if style & diff_bit_mask:
                dc.SetTextForeground(self.diff_color)
            else:
                dc.SetTextForeground(self.color)
            dc.SetFont(self.font)
            dc.DrawText(text, rect.x+1, rect.y+1)

            # Okay, now for the advanced class :)
            # Let's add three dots "..."
            # to indicate that that there is more text to be read
            # when the text is larger than the grid cell

            width, height = dc.GetTextExtent(text)
            
            if width > rect.width-2:
                width, height = dc.GetTextExtent("...")
                x = rect.x+1 + rect.width-2 - width
                dc.DrawRectangle(x, rect.y+1, width+1, height)
                dc.DrawText("...", x, rect.y+1)
            
            r, c = self.table.get_row_col(grid.editor.cursor_index)
            if row == r and col == c:
                dc.SetPen(self.cursor_pen)
                dc.SetBrush(self.cursor_brush)
                x = rect.x+1
                if sys.platform == "darwin":
                    w = rect.width - 2
                    h = rect.height - 2
                else:
                    w = rect.width - 1
                    h = rect.height - 1
                dc.DrawRectangle(rect.x+1, rect.y+1, w, h)

        dc.DestroyClippingRegion()


class ByteGridTable(Grid.PyGridTableBase):
    column_labels = [""]
    column_sizes = [4]
    
    @classmethod
    def update_preferences(cls, prefs):
        if prefs.hex_grid_lower_case:
            cls.get_value_style = cls.get_value_style_lower
        else:
            cls.get_value_style = cls.get_value_style_upper
    
    def __init__(self):
        Grid.PyGridTableBase.__init__(self)
        
        self._rows = 1
        self._cols = len(self.column_labels)
    
    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.bytes_per_row + col
        return index, index

    def get_row_col(self, index):
        return divmod(index, self.bytes_per_row)

    def is_index_valid(self, index):
        return index < self._rows * self._cols
    
    def get_col_size(self, c):
        return self.column_sizes[c]
    
    def get_col_type(self, c):
        return "hex"

    def get_next_cursor_pos(self, row, col):
        col += 1
        if col >= self._cols:
            if row < self._rows - 1:
                row += 1
                col = 0
            else:
                col = self._cols - 1
        return (row, col)
    
    def get_next_editable_pos(self, row, col):
        return self.get_next_cursor_pos(row, col)
   
    def get_prev_cursor_pos(self, row, col):
        col -= 1
        if col < 0:
            if row > 0:
                row -= 1
                col = self._cols - 1
            else:
                col = 0
        return (row, col)
   
    def get_page_index(self, index, segment_page_size, dir, grid):
        if segment_page_size < 0:
            r = grid.get_num_visible_rows()
            page_size = r * self.GetNumberCols()
        else:
            page_size = segment_page_size
        return index + (dir * page_size)

    def GetNumberRows(self):
        return self._rows

    def get_label_at_index(self, index):
        return "%s" % index

    def GetRowLabelValue(self, row):
        raise NotImplementedError

    def GetNumberCols(self):
        return self._cols

    def GetColLabelValue(self, col):
        return self.column_labels[col]
    
    def get_value_style_upper(self, row, col):
        raise NotImplementedError
    
    def get_value_style_lower(self, row, col):
        raise NotImplementedError
    
    get_value_style = get_value_style_lower
    
    def get_style_override(self, row, col, style):
        """Allow subclasses to change the style"""
        return style
    
    def GetValue(self, row, col):
        index, _ = self.get_index_range(row, col)
        if self.is_index_valid(index):
            return self.get_value_style(row, col)[0]
        return ""

    def SetValue(self, row, col, value):
        raise NotImplementedError

    def ResetViewProcessArgs(self, grid, *args):
        pass
    
    def set_grid_cell_attr(self, grid, col, attr):
        attr.SetFont(grid.editor.machine.text_font)
        attr.SetBackgroundColour("white")
        renderer = grid.get_grid_cell_renderer(self, grid.editor)
        attr.SetRenderer(renderer)
    
    def set_col_attr(self, grid, col, char_width):
        attr = Grid.GridCellAttr()
        self.set_grid_cell_attr(grid, col, attr)
        log.debug("hexcol %d width=%d" % (col, char_width))
        grid.SetColMinimalWidth(col, 0)
        grid.SetColSize(col, (char_width * self.get_col_size(col)) + 4)
        grid.SetColAttr(col, attr)

    def ResetView(self, grid, *args):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        oldrows=self._rows
        oldcols=self._cols
        self.ResetViewProcessArgs(grid, *args)
        log.debug("resetting view for %s" % grid)
        
        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (oldrows, self._rows, Grid.GRIDTABLE_NOTIFY_ROWS_DELETED, Grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (oldcols, self._cols, Grid.GRIDTABLE_NOTIFY_COLS_DELETED, Grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:

            if new < current:
                msg = Grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = Grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)
        grid.EndBatch()

        # update the scrollbars and the displayed part of the grid
        dc = wx.MemoryDC()
        dc.SetFont(grid.editor.machine.text_font)
        (width, height) = dc.GetTextExtent("M")
        grid.SetDefaultRowSize(height)
        grid.SetColMinimalAcceptableWidth(width)
        grid.SetRowMinimalAcceptableHeight(height + 1)

        for col in range(self._cols):
            # Can't share GridCellAttrs among columns; causes crash when
            # freeing them.  So, have to individually allocate the attrs for
            # each column
            self.set_col_attr(grid, col, width)

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
        
        label_font = grid.editor.machine.text_font.Bold()
        grid.SetLabelFont(label_font)
        dc.SetFont(label_font)
        (width, height) = dc.GetTextExtent("M")
        grid.SetColLabelSize(height + 4)
        text = self.GetRowLabelValue(self._rows - 1)
        grid.SetRowLabelSize(width * len(text) + 4)
        
        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = Grid.GridTableMessage(self, Grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)


class HexDigitMixin(object):
    keypad=[ wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3, 
             wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7, 
             wx.WXK_NUMPAD8, wx.WXK_NUMPAD9
             ]
    
    def isValidHexDigit(self,key):
        return key in HexDigitMixin.keypad or (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f'))

    def getValidHexDigit(self,key):
        if key in HexDigitMixin.keypad:
            return chr(ord('0') + key - wx.WXK_NUMPAD0)
        elif (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f')):
            return chr(key)
        else:
            return None


class HexTextCtrl(wx.TextCtrl,HexDigitMixin):
    def __init__(self,parent,id,parentgrid):
        # Don't use the validator here, because apparently we can't
        # reset the validator based on the columns.  We have to do the
        # validation ourselves using EVT_KEY_DOWN.
        wx.TextCtrl.__init__(self,parent, id,
                             style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER|wx.NO_BORDER)
        log.debug("parent=%s" % parent)
        self.SetInsertionPoint(0)
        self.Bind(wx.EVT_TEXT, self.on_text)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.parentgrid=parentgrid
        self.setMode('hex')
        self.startValue=None

    def setMode(self, mode):
        self.mode=mode
        if mode=='hex':
            self.SetMaxLength(2)
            self.autoadvance=2
        elif mode=='char':
            self.SetMaxLength(1)
            self.autoadvance=1
        else:
            self.SetMaxLength(0)
            self.autoadvance=0
        self.userpressed=False

    def editingNewCell(self, value, mode='hex'):
        """
        Begin editing a new cell by determining the edit mode and
        setting the initial value.
        """
        # Set the mode before setting the value, otherwise OnText gets
        # triggered before self.userpressed is set to false.  When
        # operating in char mode (i.e. autoadvance=1), this causes the
        # editor to skip every other cell.
        self.setMode(mode)
        self.startValue=value
        self.SetValue(value)
        self.SetFocus()
        self.SetInsertionPoint(0)
        self.SetSelection(-1, -1) # select the text

    def insertFirstKey(self, key):
        """
        Check for a valid initial keystroke, and insert it into the
        text ctrl if it is one.

        @param key: keystroke
        @type key: int

        @returns: True if keystroke was valid, False if not.
        """
        ch=None
        if self.mode=='hex':
            ch=self.getValidHexDigit(key)
        elif key>=wx.WXK_SPACE and key<=255:
            ch=chr(key)

        if ch is not None:
            # set self.userpressed before SetValue, because it appears
            # that the OnText callback happens immediately and the
            # keystroke won't be flagged as one that the user caused.
            self.userpressed=True
            self.SetValue(ch)
            self.SetInsertionPointEnd()
            return True

        return False

    def on_key_down(self, evt):
        """
        Keyboard handler to process command keys before they are
        inserted.  Tabs, arrows, ESC, return, etc. should be handled
        here.  If the key is to be processed normally, evt.Skip must
        be called.  Otherwise, the event is eaten here.

        @param evt: key event to process
        """
        log.debug("key down before evt=%s" % evt.GetKeyCode())
        key=evt.GetKeyCode()
        
        if key==wx.WXK_TAB:
            wx.CallAfter(self.parentgrid.advance_cursor)
            return
        elif self.mode=='hex':
            if self.isValidHexDigit(key):
                self.userpressed=True
        elif self.mode!='hex':
            self.userpressed=True
        evt.Skip()

    def cancel_edit(self):
        log.debug("cancelling edit in hex cell editor!")
        self.SetValue(self.startValue)
        self.parentgrid.cancel_edit()
        
    def on_text(self, evt):
        """
        Callback used to automatically advance to the next edit field.
        If self.autoadvance > 0, this number is used as the max number
        of characters in the field.  Once the text string hits this
        number, the field is processed and advanced to the next
        position.
        
        @param evt: CommandEvent
        """
        log.debug("evt=%s str=%s cursor=%d" % (evt,evt.GetString(),self.GetInsertionPoint()))
        
        # NOTE: we check that GetInsertionPoint returns 1 less than
        # the desired number because the insertion point hasn't been
        # updated yet and won't be until after this event handler
        # returns.
        if self.autoadvance and self.userpressed:
            if len(evt.GetString())>=self.autoadvance and self.GetInsertionPoint()>=self.autoadvance-1:
                # FIXME: problem here with a bunch of really quick
                # keystrokes -- the interaction with the
                # underlyingSTCChanged callback causes a cell's
                # changes to be skipped over.  Need some flag in grid
                # to see if we're editing, or to delay updates until a
                # certain period of calmness, or something.
                print "advancing after edit"
                wx.CallAfter(self.parentgrid.advance_cursor)


class HexCellEditor(Grid.PyGridCellEditor,HexDigitMixin):
    """
    Cell editor for the grid, based on GridCustEditor.py from the
    wxPython demo.
    """
    def __init__(self,grid):
        Grid.PyGridCellEditor.__init__(self)
        self.parentgrid=grid

    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        log.debug("")
        self._tc = HexTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def SetSize(self, rect):
        """
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.
        """
        log.debug("rect=%s\n" % rect)
        self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2,
                               wx.SIZE_ALLOW_MINUS_ONE)

    def Show(self, show, attr):
        """
        Show or hide the edit control.  You can use the attr (if not None)
        to set colours or fonts for the control.
        """
        log.debug("show=%s, attr=%s" % (show, attr))
        Grid.PyGridCellEditor.Show(self, show, attr)

    def PaintBackground(self, dc, rect, attr):
        """
        Draws the part of the cell not occupied by the edit control.  The
        base  class version just fills it with background colour from the
        attribute.  In this class the edit control fills the whole cell so
        don't do anything at all in order to reduce flicker.
        """
        log.debug("MyCellEditor: PaintBackground\n")

    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*
        """
        grid.editor.select_none(False)
        self.startValue = grid.GetTable().GetValue(row, col)
        mode = self.parentgrid.table.get_col_type(col)
        log.debug("row,col=(%d,%d), mode=%s" % (row, col, mode))
        self._tc.editingNewCell(self.startValue,mode)

    def EndEdit(self, row, col, grid, old_val):
        """
        Complete the editing of the current cell. Returns True if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        """
        log.debug("row,col=(%d,%d)" % (row, col))

        val = self._tc.GetValue()
        if val != self.startValue:
            changed = grid.change_value(row, col, val) # update the table
            # On error, don't advance cursor
            grid.change_is_valid = changed
        else:
            changed = False

        self.startValue = ''
        self._tc.SetValue('')
        return changed

    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        *Must Override*
        """
        log.debug("")
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def IsAcceptedKey(self, evt):
        """
        Return True to allow the given key to start editing: the base class
        version only checks that the event has no modifiers.  F2 is special
        and will always start the editor.
        """
        log.debug("keycode=%d" % (evt.GetKeyCode()))

        ## We can ask the base class to do it
        #return self.base_IsAcceptedKey(evt)

        # or do it ourselves
        return (not (evt.ControlDown() or evt.AltDown()) and
                evt.GetKeyCode() != wx.WXK_SHIFT)

    def StartingKey(self, evt):
        """
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.
        """
        log.debug("keycode=%d" % evt.GetKeyCode())
        key = evt.GetKeyCode()
        if not self._tc.insertFirstKey(key):
            evt.Skip()

    def StartingClick(self):
        """
        If the editor is enabled by clicking on the cell, this method will be
        called to allow the editor to simulate the click on the control if
        needed.
        """
        log.debug("")

    def Destroy(self):
        """final cleanup"""
        log.debug("")
        Grid.PyGridCellEditor.Destroy(self)

    def Clone(self):
        """
        Create a new object which is the copy of this one
        *Must Override*
        """
        log.debug("")
        return HexCellEditor(self.parentgrid)

    
class ByteGrid(Grid.Grid):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "hex"

    def __init__(self, parent, task, table, **kwargs):
        """Create the HexEdit viewer
        """
        Grid.Grid.__init__(self, parent, -1, **kwargs)
        self.task = task
        self.editor = None
        self.table = table

        # The second parameter means that the grid is to take
        # ownership of the table and will destroy it when done.
        # Otherwise you would need to keep a reference to it and call
        # its Destroy method later.
        self.SetTable(self.table, True)
        self.SetMargins(0,0)
        self.SetColMinimalAcceptableWidth(10)
        self.EnableDragGridSize(False)
        self.DisableDragRowSize()

        self.RegisterDataType(Grid.GRID_VALUE_STRING, None, None)
        e = self.get_default_cell_editor()
        self.SetDefaultEditor(e)
        self.change_is_valid = True
        self.last_change_count = 0

        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False
        self.allow_range_select = True
        self.updateUICallback = None
        self.Bind(Grid.EVT_GRID_CELL_LEFT_CLICK, self.on_left_down)
        self.Bind(Grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_left_dclick)
        self.GetGridWindow().Bind(wx.EVT_MOTION, self.on_motion)
        self.GetGridWindow().Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.GetGridWindow().Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Show(True)
    
    def __repr__(self):
        return "<%s at 0x%x>" % (self.__class__.__name__, id(self))
    
    def get_grid_cell_renderer(self, table, editor):
        return ByteGridRenderer(table, editor)

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.table.ResetView(self, editor)
            self.table.UpdateValues(self)
            self.goto_index(editor.cursor_index)
            self.last_change_count = editor.document.change_count
    
    def refresh_view(self):
        editor = self.task.active_editor
        if editor is not None:
            if self.editor != editor:
                self.recalc_view()
            elif self.IsShown():
                #self.ForceRefresh()
                if self.last_change_count == editor.document.change_count:
                    log.debug("skipping refresh; document change count=%d" % self.last_change_count)
                else:
                    log.debug("refreshing! document change count=%d" % self.last_change_count)
                    self.Refresh()
                    self.last_change_count = editor.document.change_count
            else:
                log.debug("skipping refresh of hidden %s" % self)
    
    def get_default_cell_editor(self):
        return HexCellEditor(self)

    def on_right_down(self, evt):
        log.debug(self.GetSelectedRows())
        r, c = self.get_rc_from_event(evt)
        actions = self.get_popup_actions(r, c)
        text, style = self.table.get_value_style(r, c)
        popup_data = {'row':r, 'col':c, 'index': self.table.get_index_range(r, c)[0], 'in_selection': style&0x80}
        if actions:
            self.editor.popup_context_menu_from_actions(self, actions, popup_data)
    
    def get_popup_actions(self, r, c):
        return []

    def on_left_up(self, evt):
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False

    def on_left_down(self, evt):
        self.mouse_drag_started = True
        c, r = (evt.GetCol(), evt.GetRow())
        e = self.editor
        if evt.ControlDown():
            self.multi_select_mode = True
            self.select_extend_mode = False
        elif evt.ShiftDown():
            self.multi_select_mode = False
            self.select_extend_mode = True
        if self.select_extend_mode:
            index1, index2 = self.table.get_index_range(r, c)
            if index1 < e.anchor_start_index:
                e.anchor_start_index = index1
                e.cursor_index = index1
            elif index2 > e.anchor_start_index:
                e.anchor_end_index = index2
                e.cursor_index = index2 - 1
            e.anchor_initial_start_index, e.anchor_initial_end_index = e.anchor_start_index, e.anchor_end_index
            e.select_range(e.anchor_start_index, e.anchor_end_index, add=self.multi_select_mode)
        else:
            self.ClearSelection()
            index1, index2 = self.table.get_index_range(r, c)
            e.anchor_initial_start_index, e.anchor_initial_end_index = index1, index2
            e.cursor_index = index1
            e.select_range(index1, index1, add=self.multi_select_mode)
        wx.CallAfter(e.index_clicked, e.cursor_index, 0, None)

    def get_rc_from_event(self, evt):
        x, y = evt.GetPosition()
        x1, y1 = self.CalcUnscrolledPosition(x, y)
        r, c = self.XYToCell(x1, y1)
        if r < 0:
            # XYToCell fails with (-1, -1) when the mouse is not within
            # the grid of cells.  XToCol with the second param True will
            # return a valid result when it's off the edge, but there's no
            # equivalent in YToRow (at least in 3.0 classic.  In Phoenix,
            # YToRow does support that param).
            c = self.XToCol(x1, True)
            r = self.YToRow(y1)
            if r < 0:
                if y1 < 0:
                    r = 0
                else:
                    r = self.table.GetNumberRows() - 1
        return r, c
    
    def get_num_visible_rows(self):
        ux, uy = self.GetScrollPixelsPerUnit()
        sx, sy = self.GetViewStart()
        w, h = self.GetGridWindow().GetClientSize().Get()
        y = sy * uy
        r0 = self.YToRow(y)
        r1 = self.YToRow(y + h)
        if r1 < 0:
            r1 = self.table.GetNumberRows() - 1
        return r1 - r0 - 1
 
    def on_motion(self, evt):
        self.on_motion_update_status(evt)
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        e = self.editor
        if evt.LeftIsDown():
            r, c = self.get_rc_from_event(evt)
            index1, index2 = self.table.get_index_range(r, c)
            update = False
            if self.select_extend_mode:
                if index1 < e.anchor_initial_start_index:
                    e.select_range(index1, e.anchor_initial_end_index, extend=True)
                    update = True
                else:
                    e.select_range(e.anchor_initial_start_index, index2, extend=True)
                    update = True
            else:
                if e.anchor_start_index <= index1:
                    if index2 != e.anchor_end_index:
                        e.select_range(e.anchor_initial_start_index, index2, extend=self.multi_select_mode)
                        update = True
                else:
                    if index1 != e.anchor_end_index:
                        e.select_range(e.anchor_initial_end_index, index1, extend=self.multi_select_mode)
                        update = True
            if update:
                e.cursor_index = index1
                wx.CallAfter(e.index_clicked, e.cursor_index, 0, None)
    
    def on_motion_update_status(self, evt):
        x, y = self.CalcUnscrolledPosition(evt.GetPosition())
        row = self.YToRow(y)
        col = self.XToCol(x)
        index, _ = self.table.get_index_range(row, col)
        if self.table.is_index_valid(index):
            label = self.table.get_label_at_index(index)
            message = self.get_status_message_at_index(index, row, col)
            self.editor.show_status_message("%s: %s %s" % (self.short_name, label, message))
    
    def get_status_message_at_index(self, index, row, col):
        return "r=%d,c=%d" % (row, col)

    def on_key_down(self, evt):
        e = self.editor
        key = evt.GetKeyCode()
        log.debug("evt=%s, key=%s" % (evt, key))
        moved = False
        index = None
        r, c = self.GetGridCursorRow(), self.GetGridCursorCol()
        if key == wx.WXK_RETURN or key == wx.WXK_TAB:
            if evt.ControlDown():   # the edit control needs this key
                evt.Skip()
            else:
                self.DisableCellEditControl()
                if evt.ShiftDown():
                    (r, c) = self.table.get_prev_cursor_pos(r, c)
                elif self.change_is_valid:
                    (r, c) = self.table.get_next_editable_pos(r, c)
                moved = True
                self.change_is_valid = True
        elif key == wx.WXK_RIGHT:
            r, c = self.table.get_next_cursor_pos(r, c)
            moved = True
        elif key == wx.WXK_LEFT:
            r, c = self.table.get_prev_cursor_pos(r, c)
            moved = True
        elif key == wx.WXK_UP:
            r = 0 if r <= 1 else r - 1
            moved = True
        elif key == wx.WXK_DOWN:
            n = self.GetNumberRows()
            r = n - 1 if r >= n - 1 else r + 1
            moved = True
        elif key == wx.WXK_PAGEUP:
            index = self.table.get_page_index(e.cursor_index, e.segment.page_size, -1, self)
            moved = True
        elif key == wx.WXK_PAGEDOWN:
            index = self.table.get_page_index(e.cursor_index, e.segment.page_size, 1, self)
            moved = True
        else:
            evt.Skip()
        
        if moved:
            if index is None:
                index, _ = self.table.get_index_range(r, c)
            refresh_self = None if e.can_copy else self
            e.set_cursor(index, False)
            r, c = self.table.get_row_col(e.cursor_index)
            self.SetGridCursor(r, c)
            self.MakeCellVisible(r, c)
            wx.CallAfter(e.index_clicked, e.cursor_index, 0, refresh_self)
 
    def on_left_dclick(self, evt):
        self.EnableCellEditControl()
        evt.Skip()

    def cancel_edit(self):
        log.debug("cancelling edit!")
        self.DisableCellEditControl()

    def advance_cursor(self):
        self.DisableCellEditControl()
        e = self.editor
        r, c = self.table.get_row_col(e.cursor_index)
        (r, c) = self.table.get_next_editable_pos(r, c)
        self.SetGridCursor(r, c)
        index1, index2 = self.table.get_index_range(r, c)
        e.set_cursor(index1, False)
        self.EnableCellEditControl()

    def goto_index(self, index):
        row, col = self.table.get_row_col(index)
        self.SetGridCursor(row, col)
        self.MakeCellVisible(row,col)

    def select_index(self, cursor):
        self.ClearSelection()
        self.goto_index(cursor)
        self.refresh_view()
    
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        return self.table.SetValue(row, col, text) # update the table
