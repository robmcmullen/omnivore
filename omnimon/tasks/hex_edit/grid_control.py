# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os
import struct

import wx
import wx.grid as Grid
import wx.lib.newevent

from omnimon.utils.wx.bytegrid import ByteGridTable, ByteGrid

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Grid tips:
# http://www.blog.pythonlibrary.org/2010/04/04/wxpython-grid-tips-and-tricks/


class ByteTable(ByteGridTable):
    def __init__(self, segment, bytes_per_row=16):
        ByteGridTable.__init__(self)
        
        self._debug=False
        self.bytes_per_row = bytes_per_row
        self._cols = self.bytes_per_row
        self.set_segment(segment)

    def set_segment(self, segment):
        self.segment = segment
        self._rows=((len(self.segment) - 1) / self.bytes_per_row) + 1
        log.debug("segment %s: rows=%d cols=%d len=%d" % (segment, self._rows, self.bytes_per_row, len(self.segment)))
    
    def is_index_valid(self, index):
        return index < len(self.segment)
    
    def get_col_size(self, col):
        return 2

    def getNextCursorPosition(self, row, col):
        col+=1
        if col>=self.bytes_per_row:
            if row<self._rows-1:
                row+=1
                col=0
            else:
                col=self.bytes_per_row-1
        return (row,col)
   
    def getPrevCursorPosition(self, row, col):
        col-=1
        if col<0:
            if row>0:
                row-=1
                col=self.bytes_per_row-1
            else:
                col=0
        return (row,col)
   
    def GetRowLabelValue(self, row):
        return "%04x" % (row*self.bytes_per_row + self.segment.start_addr)

    def GetColLabelValue(self, col):
        return "%x" % col
    
    def GetValue(self, row, col):
        i = row * self.bytes_per_row + col
        byte = self.segment[i]
        return "%02x" % byte

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            bytes = chr(val)
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
            
        i,_ = self.get_index(row, col)
        end = loc + len(bytes)
        
        self.segment[i:end] = bytes

    def ResetViewProcessArgs(self, segment, *args):
        self.set_segment(segment)


class HexEditControl(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, task, segment):
        """Create the HexEdit viewer
        """
        table = ByteTable(segment)
        ByteGrid.__init__(self, parent, task, table)

    def set_segment(self, segment):
        self.table.ResetView(self, segment)
        self.table.UpdateValues(self)
