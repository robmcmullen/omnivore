import sys
import time
import importlib
import inspect

import wx

from .ui import fonts

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
    display_order = [
        ("text_font", "wx.Font"),
        ("text_color", "wx.Colour"),
        ("background_color", "wx.Colour"),
        ("empty_background_color", "wx.Colour"),
        ("num_open_recent", "int"),
        ("confirm_before_close", "bool"),
    ]

    def __init__(self):
        self.text_font = fonts.str_to_font(fonts.default_font)
        self.background_color = wx.Colour(wx.WHITE)
        self.text_color = wx.Colour(wx.BLACK)
        self.empty_background_color = wx.Colour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get(False))
        self.num_open_recent = 15
        self.confirm_before_close = True

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


def find_preferences(prefs_module):
    mod = importlib.import_module(prefs_module)
    prefs_cls = SawxPreferences
    for name, obj in inspect.getmembers(mod):
        if inspect.isclass(obj) and SawxPreferences in obj.__mro__[1:]:
            prefs_cls = obj
            break
    return prefs_cls()
