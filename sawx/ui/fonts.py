import sys
import time
import importlib
import inspect

import jsonpickle

import wx

# Mapping of strings to valid wxFont families
font_families = {
    'default': wx.FONTFAMILY_DEFAULT,
    'decorative': wx.FONTFAMILY_DECORATIVE,
    'roman': wx.FONTFAMILY_ROMAN,
    'script': wx.FONTFAMILY_SCRIPT,
    'swiss': wx.FONTFAMILY_SWISS,
    'modern': wx.FONTFAMILY_MODERN
}

# Mapping of strings to wxFont styles
font_styles = {
    'slant': wx.FONTSTYLE_SLANT,
    'italic': wx.FONTSTYLE_ITALIC
}

# Mapping of strings wxFont weights
font_weights = {
    'light': wx.FONTWEIGHT_LIGHT,
    'bold': wx.FONTWEIGHT_BOLD
}

# Strings to ignore in text representations of fonts
font_noise = ['pt', 'point', 'family']

standard_font_sizes = [4, 6, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48, 56, 64, 72, 144]


if sys.platform == "darwin":
    default_font = "10 point Monaco"
elif sys.platform == "win32":
    default_font = "10 point Lucida Console"
else:
    default_font = "10 point monospace"

default_font_size = 12
default_font_index = standard_font_sizes.index(default_font_size)


# Font conversion utilities from Traitsui

def font_to_str(font):
    """ Converts a wx.Font into a string description of itself.
    """
    weight = {wx.FONTWEIGHT_LIGHT: ' Light',
              wx.FONTWEIGHT_BOLD: ' Bold'}.get(font.GetWeight(), '')
    style = {wx.FONTSTYLE_SLANT: ' Slant',
             wx.FONTSTYLE_ITALIC: ' Italic'}.get(font.GetStyle(), '')
    underline = ''
    if font.GetUnderlined():
        underline = ' underline'
    return '%s point %s%s%s%s' % (
           font.GetPointSize(), font.GetFaceName(), style, weight, underline)


def str_to_font(value):
    """ Create a wx.Font object from a string description.
    """
    point_size = None
    family = wx.FONTFAMILY_DEFAULT
    style = wx.FONTSTYLE_NORMAL
    weight = wx.FONTWEIGHT_NORMAL
    underline = 0
    facename = []
    for word in value.split():
        lword = word.lower()
        if lword in font_families:
            family = font_families[lword]
        elif lword in font_styles:
            style = font_styles[lword]
        elif lword in font_weights:
            weight = font_weights[lword]
        elif lword == 'underline':
            underline = 1
        elif lword not in font_noise:
            if point_size is None:
                try:
                    point_size = int(lword)
                    continue
                except:
                    pass
            facename.append(word)
    return wx.Font(point_size or 10, family, style, weight, underline, ' '.join(facename))


known_fonts = None  # Will be initialized in call to get_font_names


def get_font_names():
    global known_fonts

    if known_fonts is None:
        # NOTE: The list of face names from wx are in unicode
        fonts = wx.FontEnumerator()
        fonts.EnumerateFacenames()
        known_fonts = fonts.GetFacenames()
        known_fonts.sort()
        known_fonts[0:0] = ["default"]
    return known_fonts


def get_font_name(index):
    fonts = get_font_names()
    return fonts[index]


def get_font_index(face):
    fonts = get_font_names()
    try:
        return fonts.index(face)
    except ValueError:
        return 0


class wxFontHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        data["font"] = font_to_str(obj)
        return data

    def restore(self, obj):
        font_str = obj["font"]
        return str_to_font(font_str)

jsonpickle.handlers.registry.register(wx.Font, wxFontHandler)
