# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os
import struct

import wx
import wx.grid as Grid
import wx.lib.newevent

from omnivore.utils.wx.bytegrid import ByteGridTable, ByteGrid

from omnivore.framework.actions import *
from actions import *
from commands import ChangeByteCommand

import logging
log = logging.getLogger(__name__)

# Grid tips:
# http://www.blog.pythonlibrary.org/2010/04/04/wxpython-grid-tips-and-tricks/


class ByteTable(ByteGridTable):
    def __init__(self, bytes_per_row=16):
        ByteGridTable.__init__(self)
        
        self._debug=False
        self.bytes_per_row = bytes_per_row
        self._cols = self.bytes_per_row
        self._rows = 0

    def set_editor(self, editor):
        self.editor = editor
        self.segment = segment = self.editor.segment
        self.start_offset = segment.start_addr & 0x0f
        self._rows=((self.start_offset + len(segment) - 1) / self.bytes_per_row) + 1
        log.debug("segment %s: rows=%d cols=%d len=%d" % (segment, self._rows, self.bytes_per_row, len(segment)))
    
    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.bytes_per_row + col - self.start_offset
        return index, index + 1

    def get_row_col(self, index):
        return divmod(index + self.start_offset, self.bytes_per_row)

    def is_index_valid(self, index):
        return 0 <= index < len(self.segment)
    
    def get_col_size(self, col):
        return 2

    def get_value_style(self, row, col):
        i, _ = self.get_index_range(row, col)
        return "%02x" % self.segment[i], self.segment.style[i]

    def GetRowLabelValue(self, row):
        return self.segment.label(row*self.bytes_per_row - self.start_offset)

    def GetColLabelValue(self, col):
        return "%x" % col
    
    def GetValue(self, row, col):
        i, _ = self.get_index_range(row, col)
        byte = self.segment[i]
        return "%02x" % byte

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            i, _ = self.get_index_range(row, col)
            self.segment[i:i+1] = val
            return True
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value, val))
            return False

    def ResetViewProcessArgs(self, editor, *args):
        self.set_editor(editor)


class HexEditControl(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, task, **kwargs):
        """Create the HexEdit viewer
        """
        table = ByteTable()
        ByteGrid.__init__(self, parent, task, table, **kwargs)

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.table.ResetView(self, editor)
            self.table.UpdateValues(self)
    
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            val = int(text,16)
            if val >= 0 and val < 256:
                start, end = self.table.get_index_range(row, col)
                cmd = ChangeByteCommand(self.table.segment, start, end, val)
                self.task.active_editor.process_command(cmd)
        except ValueError:
            pass
        return False
    
    def get_popup_actions(self):
        return [CutAction, CopyAction, PasteAction, None, SelectAllAction, SelectNoneAction, GetSegmentFromSelectionAction]
