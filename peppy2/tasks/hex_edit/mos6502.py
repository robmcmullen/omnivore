import sys
import wx

from pyface.util.python_stc import PythonSTC, faces

from stcbase import PeppySTC
from peppy2.utils.dis6502 import get_disassembly_from_bytes

class MOS6502Disassembly(wx.Panel):

    """
    A panel for displaying and manipulating the properties of a layer.
    """
    LABEL_SPACING = 2
    VALUE_SPACING = 10
    SIDE_SPACING = 5

    def __init__(self, parent, task):
        self.task = task
        
        wx.Panel.__init__(self, parent)
        
        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.stc = PeppySTC(self)
        self.sizer.Add(self.stc, 1, wx.EXPAND | wx.ALL)
        
        self.SetSizer(self.sizer)
        self.sizer.Layout()
        self.Fit()
    
        self.set_style(wx.stc.STC_P_DEFAULT, "#000000", "#ffffff")

    def set_style(self, n, fore, back):
        self.stc.StyleSetForeground(n, fore)
        #self.StyleSetBackground(n, '#c0c0c0')
        #self.StyleSetBackground(n, '#ffffff')
        self.stc.StyleSetBackground(n, back)
        self.stc.StyleSetFaceName(n, "courier new")
        self.stc.StyleSetSize(n, faces['size'])

    def update(self, bytes):
        lines = "\n".join(get_disassembly_from_bytes(0x1000, bytes))
        self.stc.SetText(lines)
    
