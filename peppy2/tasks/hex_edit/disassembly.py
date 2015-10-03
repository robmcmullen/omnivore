import sys
import wx

from pyface.util.python_stc import PythonSTC, faces

from peppy2.utils.wx.stcbase import PeppySTC

class DisassemblyPanel(wx.Panel):

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
        
        self.disassembler = None

    def set_style(self, n, fore, back):
        self.stc.StyleSetForeground(n, fore)
        #self.StyleSetBackground(n, '#c0c0c0')
        #self.StyleSetBackground(n, '#ffffff')
        self.stc.StyleSetBackground(n, back)
        self.stc.StyleSetFaceName(n, "courier new")
        self.stc.StyleSetSize(n, faces['size'])
    
    def set_disassembler(self, disassembler):
        self.disassembler = disassembler

    def update(self, bytes):
        d = self.disassembler(bytes, 0)
        lines = "\n".join(d.get_disassembly())
        self.stc.SetText(lines)
    
    def select_pos(self, addr):
        print "make %s visible in disassembly!" % addr
