import sys

import numpy as np
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.buttons as buttons

from sawx.ui.tilelist import TileButton

import logging
log = logging.getLogger(__name__)


class TileWrapControl(wx.Panel):
    """
    View for displaying categories of tiles to paint the map
    """

    def __init__(self, parent, linked_base, command=None, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.linked_base = linked_base
        self.segment_viewer = None  # Filled in at time of segment viewer creation
        self.command_cls = command

        self.cat = wx.Choice(self, -1)
        self.cat.Bind(wx.EVT_CHOICE, self.on_category)
        self.panel = scrolled.ScrolledPanel(self, -1, style=wx.VSCROLL)
        self.panel.Bind(wx.EVT_SIZE, self.panel_size)
        psiz = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(psiz)
        self.panel.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.panel.SetupScrolling(scroll_x=False)
        self.bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.panel.SetBackgroundColour(self.bg)
        self.SetBackgroundColour(self.bg)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cat, 0, wx.EXPAND, 0)
        sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.Fit()

        self.pattern_to_item = {}
        self.parse_tile_map(self.panel, [])
        self.current_tile = None
        self.setup_tiles()
        self.zoom = 2

    @property
    def editor(self):
        return self.segment_viewer.linked_base.editor

    @property
    def task(self):
        return self.segment_viewer.linked_base.editor.task

    def panel_size(self, evt):
        size = self.panel.GetSize()
        vsize = self.panel.GetVirtualSize()
        self.panel.SetVirtualSize((size[0] - 20, vsize[1]))

    def recalc_view(self):
        if self.segment_viewer is not None:
            self.parse_tile_map(self.panel, self.segment_viewer.tile_groups)
            self.setup_tiles()
            TileButton.set_colors(self.segment_viewer.machine)

    def parse_tile_map(self, panel, tile_map):
        sizer = panel.GetSizer()
        sizer.Clear(True)
        self.tile_map = tile_map
        self.categories = []
        self.items = []
        self.pattern_to_item = {}
        for items in tile_map:
            label = items[0]
            t = wx.StaticText(panel, -1, label)
            sizer.Add(t, 0, wx.EXPAND, 0)
            self.categories.append(t)
            w = wx.WrapSizer()
            for tiles in items[1:]:
                for i in np.arange(np.alen(tiles)):
                    data = tiles[i:i+1]
                    bmp = self.segment_viewer.machine.antic_font.get_image(data[0], self.zoom)
                    btn = TileButton(panel, -1, bmp, style=wx.BORDER_NONE|wx.BU_EXACTFIT)
                    btn.SetBackgroundColour(self.bg)
                    btn.tile_data = data
                    btn.Bind(wx.EVT_BUTTON, self.on_tile_clicked)
                    w.Add(btn, 0, wx.ALL, 0)
                    self.items.append(btn)
                    self.pattern_to_item[tuple(data)] = btn
            sizer.Add(w, 0, wx.EXPAND, 0)
        self.Layout()

    def setup_tiles(self):
        cats = [str(c.GetLabelText()) for c in self.categories]
        self.cat.Set(cats)
        self.cat.SetSelection(0)

    def scroll_to_control(self, ctrl):
        sppu_x, sppu_y = self.panel.GetScrollPixelsPerUnit()
        vs_x, vs_y = self.panel.GetViewStart()
        cr = ctrl.GetRect()
        self.panel.Scroll(0, vs_y + (cr.y / sppu_y))

    def on_category(self, event):
        cat = event.GetSelection()
        label = self.categories[cat]
        self.scroll_to_control(label)

    def on_tile_clicked(self, event):
        btn = event.GetEventObject()
        self.current_tile = btn
        self.clear_toggle_except(btn)
        wx.CallAfter(self.segment_viewer.set_draw_pattern, btn.tile_data)

    def show_pattern(self, pattern):
        log.debug("tilelist showing pattern %s" % str(pattern))
        btn = self.pattern_to_item.get((int(pattern),), None)
        self.clear_toggle_except(btn)
        if btn is not None:
            self.scroll_to_control(btn)

    def clear_tile_selection(self):
        self.current_tile = None
        self.clear_toggle_except()

    def clear_toggle_except(self, btn=None):
        for b in self.items:
            if b != btn:
                b.SetToggle(False)
        if btn is not None:
            btn.SetToggle(True)

    def on_tile(self, event):
        index = event.GetInt()
        self.change_tile(self.items[index])

    def change_tile(self, tile):
        e = self.editor
        if e is None:
            return
        cmd_cls = self.command_cls
        if cmd_cls is None:
            return
        if e.can_copy:
            index = e.anchor_start_index
        else:
            index = e.caret_index
        value = tile.get_bytes()
        cmd = cmd_cls(e.segment, index, index+len(value), value, True)
        e.process_command(cmd)


if __name__ == '__main__':
    import sys
    sys.path[0:0] = [".."]
    print(sys.path)
    import omnivore.arch.fonts as fonts
    from atrip.machines import atari8bit 

    class Wrapper(object):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def set_current_draw_pattern(self, *args, **kwargs):
            pass

    class MyFrame(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.DefaultSize)
            tile_map = [
            ("road", [0x70]),
            ("trees", list(range(0x80, 0x96)), list(range(0x01, 0x16)),),
            ("buildings", list(range(0x96, 0x9f)), list(range(0x16, 0x1f)), list(range(0x41, 0x51)), list(range(0x5d, 0x60)),),
            ("people", list(range(0xf1, 0xf4)), list(range(0x71, 0x74))),
            ("water", list(range(0x2e, 0x41)),),
            ("bridges", list(range(0x69, 0x6d)),),
            ("vehicles", list(range(0x51, 0x59)),),
            ("airport", list(range(0x60, 0x68)), [0x5f], list(range(0x59, 0x5d)), list(range(0xd9, 0xdd))),
            ("golf", list(range(0xa9, 0xae)),),
            ("other", [0x20, 0x25, 0x26, ]),
            ("special", list(range(0x21, 0x25)), list(range(0x74, 0x76)),),
                ]
            color_converter = atari8bit.gtia_ntsc_to_rgb
            highlight_color = (100, 200, 230)
            unfocused_caret_color = (128, 128, 128)
            background_color = (255, 255, 255)
            match_background_color = (255, 255, 180)
            comment_background_color = (255, 180, 200)
            antic_font = fonts.AnticFont(fonts.A8DefaultFont, 4, atari8bit.powerup_colors(), highlight_color, match_background_color, comment_background_color, color_converter)
            editor = Wrapper(antic_font=antic_font, antic_tile_map=tile_map, highlight_color=highlight_color)
            task = Wrapper(active_editor=editor)
            panel = TileWrapControl(self, task)
            panel.recalc_view()

    class MyApp(wx.App):
        def OnInit(self):
            frame = MyFrame(None, -1, 'test')
            frame.Show(True)
            frame.Center()
            return True

    app = MyApp(0)
    app.MainLoop()
