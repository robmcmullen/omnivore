import hashlib
import uuid
from collections import defaultdict

import numpy as np
import wx

from sawx.persistence import iter_templates

from atrip.machines import atari8bit

from . import colors

import logging
log = logging.getLogger(__name__)

# Font is a dict (easily serializable with JSON) with the following attributes:
#    data: string containing font data
#    name: human readable name
#    x_bits: number of bits to display
#    y_bytes: number of bytes per character
#
# template:
# Font = {
#    'data_bytes': data_bytes,
#    'name':"Default Atari Font",
#    'char_w': 8,
#    'char_h': 8,
#    'uuid': uuid.UUID(bytes=hashlib.md5(data_bytes).digest()),
#    }


class AnticFont(object):
    def __init__(self, segment_viewer, font_data, font_renderer, playfield_colors, reverse=False):
        self.char_w = font_renderer.char_bit_width
        self.char_h = font_renderer.char_bit_height
        self.scale_w = font_renderer.scale_width
        self.scale_h = font_renderer.scale_height
        self.uuid = font_data['uuid']

        self.set_colors(segment_viewer, playfield_colors)
        self.set_fonts(segment_viewer, font_data, font_renderer, reverse)

    def set_colors(self, segment_viewer, playfield_colors):
        fg, bg = atari8bit.gr0_colors(playfield_colors)
        conv = segment_viewer.color_standard
        fg = conv(fg)
        bg = conv(bg)
        self.normal_gr0_colors = [fg, bg]
        prefs = segment_viewer.preferences
        self.highlight_gr0_colors = colors.get_blended_color_registers(self.normal_gr0_colors, prefs.highlight_background_color)
        self.match_gr0_colors = colors.get_blended_color_registers(self.normal_gr0_colors, prefs.match_background_color)
        self.comment_gr0_colors = colors.get_blended_color_registers(self.normal_gr0_colors, prefs.comment_background_color)
        self.data_gr0_colors = colors.get_dimmed_color_registers(self.normal_gr0_colors, prefs.background_color, prefs.data_background_color)

    def set_fonts(self, segment_viewer, font_data, font_renderer, reverse):
        if 'np_data' in font_data:
            data = font_data['np_data']
        else:
            data = np.fromstring(font_data['data_bytes'], dtype=np.uint8)
        self.font_data = font_data

        m = segment_viewer
        self.normal_font = font_renderer.get_font(data, m.color_registers, self.normal_gr0_colors, reverse)

        prefs = segment_viewer.preferences
        h_colors = colors.get_blended_color_registers(m.color_registers, prefs.highlight_background_color)
        self.highlight_font = font_renderer.get_font(data, h_colors, self.highlight_gr0_colors, reverse)

        d_colors = colors.get_dimmed_color_registers(m.color_registers, prefs.background_color, prefs.data_background_color)
        self.data_font = font_renderer.get_font(data, d_colors, self.data_gr0_colors, reverse)

        m_colors = colors.get_blended_color_registers(m.color_registers, prefs.match_background_color)
        self.match_font = font_renderer.get_font(data, m_colors, self.match_gr0_colors, reverse)

        c_colors = colors.get_blended_color_registers(m.color_registers, prefs.comment_background_color)
        self.comment_font = font_renderer.get_font(data, c_colors, self.comment_gr0_colors, reverse)

    def get_height(self, zoom):
        return self.char_h * self.scale_h * zoom

    def get_image(self, char_index, zoom, highlight=False):
        f = self.highlight_font if highlight else self.normal_font
        array = f[char_index]
        w = self.char_w
        h = self.char_h
        image = wx.Image(w, h)
        image.SetData(array.tobytes())
        w *= self.scale_w * zoom
        h *= self.scale_h * zoom
        image.Rescale(w, h)
        bmp = wx.Bitmap(image)
        return bmp


class FontListBox(wx.VListBox):
    def __init__(self, parent, font_uuids, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.SetItems(font_uuids)

    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        dc.SetFont(self.GetFont())
        dc.SetTextForeground(c)
        dc.DrawLabel(self.get_item_text(n), rect,
                     wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    def OnMeasureItem(self, n):
        height = 0
        for line in self.get_item_text(n).split('\n'):
            w, h = self.GetTextExtent(line)
            height += h
        return height + 5

    def SetItems(self, items):
        self._items = [(valid_fonts[uuid], uuid) for uuid in items]
        self._items.sort(key=lambda a:a[0]['name'])
        self.SetItemCount(len(items))

    def EnsureVisible(self, num):
        print("first: %s" % self.GetFirstVisibleLine())
        print("last: %s" % self.GetLastVisibleLine())
        self.ScrollToLine(num)

    def GetCount(self):
        return self.GetItemCount()

    def get_font(self, index):
        font, uuid = self._items[index]
        return font

    def get_item_text(self, index):
        return self.get_font(index)['name']


class FontListDialog(wx.Dialog):
    """Simple dialog to return a font from the font group
    """
    border = 5

    def __init__(self, parent, font_uuids, default, title=None, callback=None):
        if title is None:
            title = "Choose Font"
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.list = FontListBox(self, font_uuids, size=(300,400))
        try:
            index = font_uuids.index(default)
        except ValueError:
            index = 0
        self.list.SetSelection(index)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        sizer.Add(btnsizer, 0, wx.EXPAND, 0)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

        self.list.Bind(wx.EVT_LISTBOX, self.on_click)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_click)
        self.callback = callback

    def on_click(self, evt):
        if evt.IsSelection() or True:
            index = evt.GetSelection()
            font = self.list.get_font(index)
            log.debug(f"index={index} font={font['name']}")
            if self.callback:
                self.callback(font)

    def show_and_get_font(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            index = self.list.GetSelection()
            font = self.list.get_font(index)
        else:
            font = None
        self.Destroy()
        return font


class FontGroupDialog(FontListDialog):
    def __init__(self, parent, font_group_name, default=None, callback=None):
        font_uuids = font_groups[font_group_name]
        FontListDialog.__init__(self, parent, font_uuids, default, f"Choose Font From {font_group_name}", callback)


def prompt_for_font_from_group(parent, font_group_name, callback=None):
    d = FontGroupDialog(parent, font_group_name, callback=callback)
    return d.show_and_get_font()


font_list = []

font_groups = {}

valid_fonts = {}

def restore_from_last_time():
    global font_list, font_groups, valid_fonts

    log.debug("Restoring known fonts")
    groups = defaultdict(list)
    for template in iter_templates("font"):
        template['data_bytes'] = template.data_bytes
        valid_fonts[template['uuid']] = template
        log.debug(f"found font {template} at {template.data_file_path}")
        if "font_group" in template:
            groups[template['font_group']].append(template['uuid'])
        else:
            font_list.append(template)
    font_groups = groups
    font_list.sort()


def remember_for_next_time():
    log.debug("Remembering fonts")
