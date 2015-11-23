import sys
import wx

import wx.grid as Grid

import logging
log = logging.getLogger(__name__)


class ByteGridRenderer(Grid.PyGridCellRenderer):
    def __init__(self, table, editor):
        """Render data in the specified color and font and fontsize"""
        Grid.PyGridCellRenderer.__init__(self)
        self.table = table
        self.color = editor.text_color
        self.font = editor.text_font
        self.selected_background = editor.highlight_color
        self.selected_brush = wx.Brush(editor.highlight_color, wx.SOLID)
        self.selected_pen = wx.Pen(editor.highlight_color, 1, wx.SOLID)
        self.normal_background = editor.background_color
        self.normal_brush = wx.Brush(editor.background_color, wx.SOLID)
        self.normal_pen = wx.Pen(editor.background_color, 1, wx.SOLID)
        self.colSize = None
        self.rowSize = 50

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
            start, end = grid.editor.anchor_start_index, grid.editor.anchor_end_index
            if start > end:
                start, end = end, start
#            print "r,c,index", row, col, index, "grid selection:", start, end
            is_in_range = start <= index < end
            if is_in_range:
                dc.SetBrush(self.selected_brush)
                dc.SetPen(self.selected_pen)
                dc.SetTextBackground(self.selected_background)
            else:
                dc.SetBrush(self.normal_brush)
                dc.SetPen(self.normal_pen)
                dc.SetTextBackground(self.normal_background)
            dc.DrawRectangleRect(rect)

            text = self.table.GetValue(row, col)
            dc.SetBackgroundMode(wx.SOLID)

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

        dc.DestroyClippingRegion()


class ByteGridTable(Grid.PyGridTableBase):
    column_labels = [""]
    column_sizes = [4]
    
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
   
    def GetNumberRows(self):
        return self._rows

    def GetRowLabelValue(self, row):
        raise NotImplementedError

    def GetNumberCols(self):
        return self._cols

    def GetColLabelValue(self, col):
        return self.column_labels[col]
    
    def GetValue(self, row, col):
        raise NotImplementedError

    def SetValue(self, row, col, value):
        raise NotImplementedError

    def ResetViewProcessArgs(self, *args):
        pass
    
    def set_grid_cell_attr(self, grid, col, attr):
        attr.SetFont(grid.editor.text_font)
        attr.SetBackgroundColour("white")
        renderer = ByteGridRenderer(self, grid.editor)
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
        self.ResetViewProcessArgs(*args)
        
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
        dc.SetFont(grid.editor.text_font)
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
        
        label_font = grid.editor.text_font.Bold()
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
                             style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        log.debug("parent=%s" % parent)
        self.SetInsertionPoint(0)
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
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

    def OnKeyDown(self, evt):
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
        
    def OnText(self, evt):
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
        print "IN END EDIT"
        log.debug("row,col=(%d,%d)" % (row, col))
        changed = False

        val = self._tc.GetValue()
        
        if val != self.startValue:
            changed = grid.change_value(row, col, val) # update the table

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

        self.select_extend_mode = False
        self.allow_range_select = True
        self.updateUICallback = None
        self.Bind(Grid.EVT_GRID_CELL_LEFT_CLICK, self.OnLeftDown)
        self.GetGridWindow().Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(Grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)
#        self.Bind(Grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
#        self.Bind(Grid.EVT_GRID_RANGE_SELECT, self.OnSelectRange)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Show(True)
    
    def get_default_cell_editor(self):
        return HexCellEditor(self)

    def OnRightDown(self, evt):
        log.debug(self.GetSelectedRows())
        actions = self.get_popup_actions()
        if actions:
            self.editor.popup_context_menu_from_actions(self, actions)
    
    def get_popup_actions(self):
        return []

    def OnLeftDown(self, evt):
        c, r = (evt.GetCol(), evt.GetRow())
        e = self.editor
        self.select_extend_mode = evt.ShiftDown()
        if self.select_extend_mode:
            index1, index2 = self.table.get_index_range(r, c)
            if index1 < e.anchor_start_index:
                e.anchor_start_index = index1
            elif index2 > e.anchor_start_index:
                e.anchor_end_index = index2
            e.anchor_initial_start_index, e.anchor_initial_end_index = e.anchor_start_index, e.anchor_end_index
        else:
            self.ClearSelection()
            e.anchor_initial_start_index, e.anchor_initial_end_index = self.table.get_index_range(r, c)
            e.anchor_start_index, e.anchor_end_index = e.anchor_initial_start_index, e.anchor_initial_end_index
            evt.Skip()
        self.SetGridCursor(r, c)
        wx.CallAfter(self.ForceRefresh)
        wx.CallAfter(self.task.active_editor.index_clicked, e.anchor_start_index, 0, self)
 
    def on_motion(self, evt):
        e = self.editor
        if evt.LeftIsDown():
            x, y = evt.GetPosition()
            x, y = self.CalcUnscrolledPosition(x, y)
            r, c = self.XYToCell(x, y)
            index1, index2 = self.table.get_index_range(r, c)
            update = False
            if evt.ShiftDown():
                if not self.select_extend_mode:
                    # Shift pressed during drag; turn into extend mode
                    e.anchor_initial_start_index, e.anchor_initial_end_index = e.anchor_start_index, e.anchor_end_index
                if index1 < e.anchor_initial_start_index:
                    e.anchor_start_index = index1
                    e.anchor_end_index = e.anchor_initial_end_index
                    update = True
                else:
                    e.anchor_start_index = e.anchor_initial_start_index
                    e.anchor_end_index = index2
                    update = True
            else:
                if e.anchor_start_index <= index1:
                    if index2 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_start_index
                        e.anchor_end_index = index2
                        update = True
                else:
                    if index1 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_end_index
                        e.anchor_end_index = index1
                        update = True
            self.select_extend_mode = evt.ShiftDown()
            if update:
                self.SetGridCursor(r, c)
                wx.CallAfter(self.ForceRefresh)
                wx.CallAfter(self.task.active_editor.index_clicked, e.anchor_end_index, 0, self)
        evt.Skip()

    def OnSelectCell(self, evt):
        log.debug("cell selected r=%d c=%d" % (evt.GetCol(), evt.GetRow()))
        evt.Skip()

    def OnKeyDown(self, evt):
        key = evt.GetKeyCode()
        log.debug("evt=%s, key=%s" % (evt, key))
        moved = False
        r, c = self.GetGridCursorRow(), self.GetGridCursorCol()
        if key == wx.WXK_RETURN or key == wx.WXK_TAB:
            if evt.ControlDown():   # the edit control needs this key
                evt.Skip()
            else:
                self.DisableCellEditControl()
                if evt.ShiftDown():
                    (r, c) = self.table.get_prev_cursor_pos(r, c)
                else:
                    (r, c) = self.table.get_next_editable_pos(r, c)
                moved = True
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
        else:
            evt.Skip()
        
        if moved:
            self.SetGridCursor(r, c)
            self.MakeCellVisible(r, c)
            index1, index2 = self.table.get_index_range(r, c)
            wx.CallAfter(self.task.active_editor.index_clicked, index1, 0, self)

    def cancel_edit(self):
        log.debug("cancelling edit!")
        self.DisableCellEditControl()

    def advance_cursor(self):
        self.DisableCellEditControl()
        # FIXME: moving from the hex region to the value region using
        # self.MoveCursorRight(False) causes a segfault, so make sure
        # to stay in the same region
        (row,col)=self.table.get_next_editable_pos(self.GetGridCursorRow(),self.GetGridCursorCol())
        self.SetGridCursor(row,col)
        self.EnableCellEditControl()

    def goto_index(self, index):
        row, col = self.table.get_row_col(index)
        self.SetGridCursor(row, col)
        self.MakeCellVisible(row,col)

    def select_index(self, cursor):
        self.ClearSelection()
        self.goto_index(cursor)
        self.ForceRefresh()
    
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        return self.table.SetValue(row, col, text) # update the table
