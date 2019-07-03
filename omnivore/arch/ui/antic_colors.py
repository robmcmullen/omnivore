import numpy as np

import wx
import wx.lib.buttons as buttons
import wx.lib.sized_controls as sc
import wx.lib.colourselect as csel
import wx.lib.colourchooser.canvas as canvas

from atrip.machines import atari8bit


#704  2C0  PCOLR0
#705  2C1  PCOLR1
#706  2C2  PCOLR2
#707  2C3  PCOLR3
#708  2C4  COLOR0
#709  2C5  COLOR1
#710  2C6  COLOR2
#711  2C7  COLOR3
#712  2C8  COLOR4 (Background/Border)

default_color_register_names = ["%d (%x) %s" % (i + 704, i + 704, n) for i, n in enumerate([
    "Player 0",
    "Player 1",
    "Player 2",
    "Player 3",
    "Playfield 0",
    "Playfield 1",
    "Playfield 2",
    "Playfield 3",
    "Background",
    ])]


class ColorListBox(wx.VListBox):
    def calc_sizes(self):
        self.max_w = 0
        n = 0
        while True:
            try:
                label = self.get_label(n)
            except IndexError:
                break
            w, h = self.GetTextExtent(label)
            if w > self.max_w:
                self.max_w = w
            n += 1

    def get_label(self, n):
        names = self.GetParent().color_register_names
        return names[n]

    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        dc.SetFont(self.GetFont())
        dc.SetTextForeground(c)
        label = self.get_label(n)
        dc.DrawLabel(label, rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        color = self.GetParent().get_color(n)
        dc.SetBrush(wx.Brush(color))
        rect.Offset(self.max_w, 0)
        rect.Deflate(2, 2)
        dc.DrawRectangle(rect)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        label = self.get_label(n)
        w, h = self.GetTextExtent(label)
        return h + 5


class AnticPalette(canvas.Canvas):
    """Large image selection using Antic colors
    """

    HORIZONTAL_STEP = 24
    VERTICAL_STEP = 24
    BORDER = 4
    HIGHLIGHT_WIDTH = 5

    def __init__(self, parent, color_prefs):
        """Creates a palette object."""
        # Load the pre-generated palette XPM

        # Leaving this in causes warning messages in some cases.
        # It is the responsibility of the app to init the image
        # handlers, IAW RD
        #wx.InitAllImageHandlers()
        self.color_prefs = color_prefs
        self.palette = self.init_palette()
        size = self.palette.GetSize()
        canvas.Canvas.__init__(self, parent, -1, style=wx.SIMPLE_BORDER, forceClientSize=size)

    def init_palette(self):
        w = self.HORIZONTAL_STEP * 16 + 2 * self.BORDER
        h = self.VERTICAL_STEP * 16 + 2 * self.BORDER
        array = np.empty((h, w, 3), dtype=np.uint8)
        array[:,:] = self.color_prefs.empty_background_color[:3]
        for high in range(0, 256, 16):
            y = self.BORDER + (high // 16) * self.VERTICAL_STEP
            for low in range(16):
                x = self.BORDER + low * self.HORIZONTAL_STEP
                c = atari8bit.gtia_ntsc_to_rgb(high + low)
                array[y:y+self.VERTICAL_STEP,x:x+self.HORIZONTAL_STEP,:] = c
        width = array.shape[1]
        height = array.shape[0]
        image = wx.Image(width, height)
        image.SetData(array.tobytes())
        bmp = wx.Bitmap(image)
        return bmp

    def DrawBuffer(self):
        """Draws the palette XPM into the memory buffer."""
        #self.GeneratePaletteBMP ("foo.bmp")
        self.buffer.DrawBitmap(self.palette, 0, 0, 0)

    def highlight_xy(self, x, y):
        """Highlights an area of the palette with a rectangle around
        the coordinate point"""
        low = (x - self.BORDER) // self.HORIZONTAL_STEP
        high = (y - self.BORDER) // self.VERTICAL_STEP
        return self.highlight(high, low)

    def highlight_color(self, c):
        high, low = divmod(c, 16)
        return self.highlight(high, low)

    def highlight(self, high, low):
        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        self.buffer.SetPen(wx.Pen(colour, self.HIGHLIGHT_WIDTH, wx.SOLID))
        self.buffer.SetBrush(wx.Brush(colour, wx.TRANSPARENT))
        low = 15 if low > 15 else low
        low = 0 if low < 0 else low
        high = 15 if high > 15 else high
        high = 0 if high < 0 else high
        x = self.BORDER + low * self.HORIZONTAL_STEP
        y = self.BORDER + high * self.VERTICAL_STEP
        self.buffer.DrawRectangle(x, y, self.HORIZONTAL_STEP, self.VERTICAL_STEP)
        self.Refresh()
        return high * 16 + low


class AnticColorDialog(wx.Dialog):
    def __init__(self, parent, antic_color_registers, color_prefs, color_register_names=None):
        wx.Dialog.__init__(self, parent, -1, "Choose ANTIC Colors")
        self.num_cols = 17
        if color_register_names is None:
            self.color_register_names = default_color_register_names
        else:
            self.color_register_names = color_register_names

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.name = wx.StaticText(self, -1, "Editing Color")
        sizer.Add(self.name, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.color_registers = ColorListBox(self, -1, style=wx.VSCROLL, size=(200, -1))
        box.Add(self.color_registers, 0, wx.EXPAND|wx.ALL, 4)
        self.palette = AnticPalette(self, color_prefs)
        box.Add(self.palette, 1, wx.ALL, 4)
        sizer.Add(box, 1, wx.GROW|wx.ALL, 5)

        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btn_sizer, 0, wx.GROW|wx.ALL, 12)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_LISTBOX, self.on_set_register)
        self.mouse_down = False
        self.palette.Bind(wx.EVT_LEFT_DOWN, self.onPaletteDown)
        self.palette.Bind(wx.EVT_LEFT_UP, self.onPaletteUp)
        self.palette.Bind(wx.EVT_MOTION, self.onPaletteMotion)

        self.init_colors(antic_color_registers)

        # Need SetSizeHints to force the window to fit the size of the sizer. From
        # http://wxpython.org/Phoenix/docs/html/sizers_overview.html#sizers-overview
        sizer.SetSizeHints(self)
        self.SetSizer(sizer)
        self.Layout()
        self.Fit()

    def init_colors(self, antic_color_registers):
        self.color_registers.calc_sizes()
        c = list(antic_color_registers)
        if len(c) == 5:
            self.colors = list([0, 0, 0, 0])
            self.colors.extend(list(c))
        else:
            self.colors = c
        self.color_registers.SetItemCount(9)
        self.current_register = 4
        self.color_registers.SetSelection(self.current_register)

    def get_color(self, register):
        return atari8bit.gtia_ntsc_to_rgb(self.colors[register])

    def on_button(self, event):
        if event.GetId() == wx.ID_OK:
            self.EndModal(wx.ID_OK)
            event.Skip()
        else:
            self.EndModal(wx.ID_CANCEL)
            event.Skip()

    def on_close(self, event):
        self.EndModal(wx.ID_CANCEL)
        event.Skip()

    def on_set_register(self, event):
        self.current_register = event.GetSelection()
        color = self.colors[self.current_register]
        self.palette.ReDraw()
        self.palette.highlight_color(color)

    def on_set_color(self, event):
        id = event.GetId()
        b, c = self.toggles[id]
        self.colors[self.current_register] = c
        self.color_registers.Refresh()

    def onPaletteDown(self, event):
        """Stores state that the mouse has been pressed and updates
        the selected colour values."""
        self.mouse_down = True
        self.palette.ReDraw()
        self.doPaletteClick(event.X, event.Y)

    def onPaletteUp(self, event):
        """Stores state that the mouse is no longer depressed."""
        self.mouse_down = False

    def onPaletteMotion(self, event):
        """Updates the colour values during mouse motion while the
        mouse button is depressed."""
        if self.mouse_down:
            self.doPaletteClick(event.X, event.Y)

    def doPaletteClick(self, m_x, m_y):
        """Updates the colour values based on the mouse location
        over the palette."""
        # Highlight a fresh selected area
        self.palette.ReDraw()
        c = self.palette.highlight_xy(m_x, m_y)
        self.colors[self.current_register] = c
        self.color_registers.Refresh()


if __name__ == "__main__":
    """
    simple test for the dialog
    """
    from omnivore.arch.machine import Machine

    a = wx.App(False)
    import wx.lib.inspection
    wx.lib.inspection.InspectionTool().Show()
    w = wx.Frame(None)
    attr = w.GetDefaultAttributes()
    antic_color_registers = [40, 202, 148, 70, 0]
    Machine.empty_color = attr.colBg.Get(False)
    d = AnticColorDialog(w, antic_color_registers)
    d.Show()
    a.MainLoop()
