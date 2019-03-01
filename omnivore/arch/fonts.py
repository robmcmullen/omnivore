import hashlib
import uuid

import numpy as np
import wx

from omnivore_framework.templates import iter_templates

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
        fg, bg = colors.gr0_colors(playfield_colors)
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


font_list = []

valid_fonts = {}

def restore_from_last_time():
    global font_list, valid_fonts

    log.debug("Restoring known fonts")
    for template in iter_templates("font"):
        template['data_bytes'] = template.data_bytes
        valid_fonts[template['uuid']] = template
        log.debug(f"found font {template} at {template.data_file_path}")
        font_list.append(template)
    font_list.sort()


def remember_for_next_time():
    log.debug("Remembering fonts")
