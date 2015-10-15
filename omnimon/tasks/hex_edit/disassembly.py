import sys
import wx

import wx.grid as Grid

from omnimon.utils.binutil import DefaultSegment

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class MegaFontRenderer(Grid.PyGridCellRenderer):
    def __init__(self, table, color="black", font="ARIAL", fontsize=8):
        """Render data in the specified color and font and fontsize"""
        Grid.PyGridCellRenderer.__init__(self)
        self.table = table
        self.color = color
        self.font = wx.Font(fontsize, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, font)
        self.selectedBrush = wx.Brush("blue", wx.SOLID)
        self.normalBrush = wx.Brush(wx.WHITE, wx.SOLID)
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
        
        start, end = grid.anchor_index, grid.end_index
        if start > end:
            start, end = end, start
#        print "r,c", row, col, "grid selection:", start, end
        is_in_range = start <= row <= end
        if isSelected or is_in_range:
            dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
        else:
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
        dc.DrawRectangleRect(rect)

        text = self.table.GetValue(row, col)
        dc.SetBackgroundMode(wx.SOLID)

        # change the text background based on whether the grid is selected
        # or not
        if isSelected or is_in_range:
            dc.SetBrush(self.selectedBrush)
            dc.SetTextBackground("blue")
        else:
            dc.SetBrush(self.normalBrush)
            dc.SetTextBackground("white")

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


class DisassemblyTable(Grid.PyGridTableBase):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [8, 12, 20]
    
    def __init__(self, segment):
        Grid.PyGridTableBase.__init__(self)
        
        self.disassembler = None
        self._cols = 3
        self.set_segment(segment)

    def set_segment(self, segment):
        self.segment = segment
        lines = []
        addr_map = {}
        if self.disassembler is not None:
            d = self.disassembler(segment.data, segment.start_addr, -segment.start_addr)
            for i, (addr, bytes, opstr, comment) in enumerate(d.get_disassembly()):
                lines.append((addr, bytes, opstr, comment))
                addr_map[addr] = i
        self.lines = lines
        self.addr_to_lines = addr_map
        if self.lines:
            self.start_addr = self.lines[0][0]
        else:
            self.start_addr = 0

        self._rows = len(self.lines)
   
    def GetNumberRows(self):
        log.debug("rows = %d" % self._rows)
        return self._rows

    def GetRowLabelValue(self, row):
        line = self.lines[row]
        return "%04x" % line[0]

    def GetNumberCols(self):
        log.debug("cols = %d" % self._cols)
        return self._cols

    def GetColLabelValue(self, col):
        return self.column_labels[col]
    
    def GetValue(self, row, col):
        line = self.lines[row]
        return str(line[col + 1])

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            bytes = chr(val)
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
            
        i = self.get_index(row, col)
        end = loc + len(bytes)
        
        self.segment[i:end] = bytes

    def ResetView(self, grid, segment):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        oldrows=self._rows
        oldcols=self._cols
        self.set_segment(segment)
        
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
        grid.SetColMinimalAcceptableWidth(0)
        font=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL)
        dc=wx.MemoryDC()
        dc.SetFont(font)
        
        (width, height) = dc.GetTextExtent("M")
        grid.SetDefaultRowSize(height)
        
        for col in range(self._cols):
            # Can't share GridCellAttrs among columns; causes crash when
            # freeing them.  So, have to individually allocate the attrs for
            # each column
            hexattr = Grid.GridCellAttr()
            hexattr.SetFont(font)
            hexattr.SetBackgroundColour("white")
            renderer = MegaFontRenderer(self)
            hexattr.SetRenderer(renderer)
            log.debug("hexcol %d width=%d" % (col,width))
            grid.SetColMinimalWidth(col, 0)
            grid.SetColSize(col, (width * self.column_sizes[col]) + 4)
            grid.SetColAttr(col, hexattr)

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = Grid.GridTableMessage(self, Grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)

class DisassemblyPanel(Grid.Grid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, task, segment=None):
        """Create the HexEdit viewer
        """
        Grid.Grid.__init__(self, parent, -1)
        self.task = task
        if segment is None:
            segment = DefaultSegment()
        self.table = DisassemblyTable(segment)

        # The second parameter means that the grid is to take
        # ownership of the table and will destroy it when done.
        # Otherwise you would need to keep a reference to it and call
        # its Destroy method later.
        self.SetTable(self.table, True)
        self.SetMargins(0,0)
        self.SetColMinimalAcceptableWidth(10)
        self.EnableDragGridSize(False)

        self.RegisterDataType(Grid.GRID_VALUE_STRING, None, None)
#        self.SetDefaultEditor(HexCellEditor(self))

        self.anchor_index = None
        self.end_index = None
        self.allow_range_select = True
        self.updateUICallback = None
        self.Bind(Grid.EVT_GRID_CELL_LEFT_CLICK, self.OnLeftDown)
        self.GetGridWindow().Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(Grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)
#        self.Bind(Grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
#        self.Bind(Grid.EVT_GRID_RANGE_SELECT, self.OnSelectRange)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Show(True)

    def set_segment(self, segment):
        self.table.ResetView(self, segment)
        self.table.UpdateValues(self)

    def set_disassembler(self, d):
        self.table.disassembler = d
        
    def OnRightDown(self, evt):
        log.debug(self.GetSelectedRows())

    def OnLeftDown(self, evt):
        c, r = (evt.GetCol(), evt.GetRow())
        self.ClearSelection()
        self.anchor_index = r
        self.end_index = self.anchor_index
        print "down: cell", (c, r)
        evt.Skip()
        wx.CallAfter(self.ForceRefresh)
 
    def on_motion(self, evt):
        if self.anchor_index is not None and evt.LeftIsDown():
            x, y = evt.GetPosition()
            x, y = self.CalcUnscrolledPosition(x, y)
            r, c = self.XYToCell(x, y)
            index = r
            if index != self.end_index:
                self.end_index = index
                wx.CallAfter(self.ForceRefresh)
            print "motion: x, y, index", x, y, index
        evt.Skip()

    def OnSelectCell(self, evt):
        print "cell selected:", evt.GetCol(), evt.GetRow()
        evt.Skip()

    def OnKeyDown(self, evt):
        log.debug("evt=%s" % evt)
        if evt.GetKeyCode() == wx.WXK_RETURN or evt.GetKeyCode()==wx.WXK_TAB:
            if evt.ControlDown():   # the edit control needs this key
                evt.Skip()
            else:
                self.DisableCellEditControl()
                if evt.ShiftDown():
                    (row,col)=self.GetTable().getPrevCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
                else:
                    (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
                self.SetGridCursor(row,col)
                self.MakeCellVisible(row,col)
        else:
            evt.Skip()

    def abortEdit(self):
        self.DisableCellEditControl()

    def advanceCursor(self):
        self.DisableCellEditControl()
        # FIXME: moving from the hex region to the value region using
        # self.MoveCursorRight(False) causes a segfault, so make sure
        # to stay in the same region
        (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
        self.SetGridCursor(row,col)
        self.EnableCellEditControl()
    
    def pos_to_row(self, pos):
        addr = pos + self.GetTable().start_addr
        addr_map = self.GetTable().addr_to_lines
        if addr in addr_map:
            index = addr_map[addr]
        else:
            index = 0
            for a in range(addr - 1, addr - 5, -1):
                if a in addr_map:
                    index = addr_map[a]
                    break
        print "addr %s -> index=%d" % (addr, index)
        return index

    def select_pos(self, pos):
        print "make %s visible in disassembly!" % pos
        row = self.pos_to_row(pos)
        self.select_range(row, row)
        self.SetGridCursor(row, 0)
        self.MakeCellVisible(row, 0)
    
    def select_range(self, start, end):
        self.ClearSelection()
        self.anchor_index = start
        self.end_index = end
        self.ForceRefresh()
