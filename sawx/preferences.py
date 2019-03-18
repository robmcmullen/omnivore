import sys
import time

import wx

if sys.platform == "darwin":
    def_font = "10 point Monaco"
elif sys.platform == "win32":
    def_font = "10 point Lucida Console"
else:
    def_font = "10 point monospace"

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


def str_to_font(value):
    """ Create a TraitFont object from a string description.
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
    return wx.Font(point_size or 10, family, style, weight, underline,
                      ' '.join(facename))

class cached_property:
    """Decorator for read-only properties evaluated only once until invalidated.

    It can be used to create a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):
            # create property whose value is cached for ten minutes
            @cached_property
            def randint(self):
                # will only be evaluated once unless invalidated
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object instance that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    To expire a cached property value manually just do::

        del instance._cache[<property name>]

    """
    def __init__(self, func, doc=None):
        self.func = func
        self.__doc__ = doc or func.__doc__
        self.__name__ = func.__name__
        self.__module__ = func.__module__

    def __get__(self, inst, owner):
        try:
            value = inst._cache[self.__name__]
        except (KeyError, AttributeError):
            value = self.func(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = value
        return value


class SawxPreferences:
    def __init__(self):
        self.text_font = str_to_font(def_font)
        self.background_color = wx.Colour(wx.WHITE)
        self.text_color = wx.Colour(wx.BLACK)
        self.empty_background_color = wx.Colour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get(False))

    @property
    def text_font(self):
        return self._text_font

    @text_font.setter
    def text_font(self, value):
        self._text_font = value
        dc = wx.MemoryDC()
        dc.SetFont(self._text_font)
        self.text_font_char_width = dc.GetCharWidth()
        self.text_font_char_height = dc.GetCharHeight()
