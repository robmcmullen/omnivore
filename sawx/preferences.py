import sys
import time
import importlib
import inspect

import wx

from . import persistence
from .events import EventHandler
from .ui import fonts

import logging
log = logging.getLogger(__name__)


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
    display_title = None

    display_order = [
    ]

    def __init__(self, module_path):
        self._module_path = module_path
        self.set_defaults()
        self.preferences_changed_event = EventHandler(self)

    def __eq__(self, other):
        if hasattr(other, "display_order") and self.display_order == other.display_order:
            for d in self.display_order:
                attrib_name = d[0]
                if getattr(self, attrib_name) != getattr(other, attrib_name):
                    break
            else:
                return True
        return False

    def set_defaults(self):
        self._image_caches = {}

    def calc_image_cache(self, cache_cls):
        try:
            c = self._image_caches[cache_cls]
        except KeyError:
            c = cache_cls(self)
            self._image_caches[cache_cls] = c
        return c

    def copy_from(self, other):
        for d in self.display_order:
            attrib_name = d[0]
            try:
                value = getattr(other, attrib_name)
            except AttributeError:
                try:
                    value = other[attrib_name]
                except KeyError:
                    continue
            try:
                setattr(self, attrib_name, value)
            except Exception:
                log.error(f"{self._module_path}: failed setting {attrib_name} to {value}")

    def clone(self):
        other = self.__class__(self._module_path)
        other.copy_from(self)
        return other

    def restore_user_settings(self):
        settings = persistence.get_json_data(self._module_path)
        log.debug(f"restore_user_overrides: user data = {settings}")
        if settings is not None:
            settings_dict = dict(settings)
            self.copy_from(settings_dict)

    def persist_user_settings(self):
        settings = [[d[0], getattr(self, d[0])] for d in self.display_order]
        log.debug(f"persist_user_settings: Saving {settings}")
        path = persistence.save_json_data(self._module_path, settings)
        log.debug(f"persist_user_settings: Saved to {path}")
        self.preferences_changed_event(True)



class SawxApplicationPreferences(SawxPreferences):
    ui_name = "General"

    display_order = [
        ("num_open_recent", "int", "Number of files in Open Recent menu"),
        ("confirm_before_close", "bool"),
    ]

    def set_defaults(self):
        SawxPreferences.set_defaults(self)
        self.num_open_recent = 15
        self.confirm_before_close = True


class SawxEditorPreferences(SawxPreferences):
    display_order = [
        ("text_font", "wx.Font"),
        ("text_color", "wx.Colour"),
        ("diff_text_color", "wx.Colour"),

        ("background_color", "wx.Colour"),
        ("highlight_background_color", "wx.Colour"),
        ("data_background_color", "wx.Colour"),
        ("match_background_color", "wx.Colour"),
        ("comment_background_color", "wx.Colour"),
        ("error_background_color", "wx.Colour"),
        ("empty_background_color", "wx.Colour"),

        ("unfocused_caret_color", "wx.Colour"),

        ("header_font", "wx.Font"),
        ("row_header_bg_color", "wx.Colour"),
        ("row_label_border_width", "int"),
        ("row_height_extra_padding", "int"),
        ("col_header_bg_color", "wx.Colour"),
        ("col_label_border_width", "int"),
        ("cell_padding_width", "int"),
    ]

    def set_defaults(self):
        SawxPreferences.set_defaults(self)
        self.text_font = fonts.str_to_font(fonts.default_font)
        self._background_color = wx.Colour(wx.WHITE)
        self.text_color = wx.Colour(wx.BLACK)
        self._empty_background_color = wx.Colour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get(False))
        self.header_font = fonts.str_to_font(fonts.default_font + "bold")
        self.row_header_bg_color = wx.Colour(224, 224, 224)
        self.col_header_bg_color = wx.Colour(224, 224, 224)
        self.col_label_border_width = 3
        self.row_label_border_width = 3
        self.row_height_extra_padding = -3
        self.base_cell_width_in_chars = 2
        self.cell_padding_width = 2

        self.unfocused_caret_color = wx.Colour(128, 128, 128)
        self._highlight_background_color = wx.Colour(100, 200, 230)
        self._data_background_color = wx.Colour(224, 224, 224)
        self._match_background_color = wx.Colour(255, 255, 180)
        self._comment_background_color = wx.Colour(255, 180, 200)
        self.error_background_color = wx.Colour(255, 128, 128)
        self.diff_text_color = wx.Colour(255, 0, 0)

        self.caret_pen = wx.Pen(self.unfocused_caret_color, 1, wx.SOLID)

        self.selected_brush = wx.Brush(self.highlight_background_color, wx.SOLID)
        self.normal_brush = wx.Brush(self.background_color, wx.SOLID)
        self.data_brush = wx.Brush(self.data_background_color, wx.SOLID)
        self.match_brush = wx.Brush(self.match_background_color, wx.SOLID)
        self.comment_brush = wx.Brush(self.comment_background_color, wx.SOLID)
        self.empty_brush = wx.Brush(self.empty_background_color, wx.SOLID)

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

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, value):
        self._background_color = value
        self.normal_brush = wx.Brush(self.background_color, wx.SOLID)

    @property
    def highlight_background_color(self):
        return self._highlight_background_color

    @highlight_background_color.setter
    def highlight_background_color(self, value):
        self._highlight_background_color = value
        self.selected_brush = wx.Brush(self.highlight_background_color, wx.SOLID)

    @property
    def data_background_color(self):
        return self._data_background_color

    @data_background_color.setter
    def data_background_color(self, value):
        self._data_background_color = value
        self.data_brush = wx.Brush(self.data_background_color, wx.SOLID)

    @property
    def match_background_color(self):
        return self._match_background_color

    @match_background_color.setter
    def match_background_color(self, value):
        self._match_background_color = value
        self.match_brush = wx.Brush(self.match_background_color, wx.SOLID)

    @property
    def comment_background_color(self):
        return self._comment_background_color

    @comment_background_color.setter
    def comment_background_color(self, value):
        self._comment_background_color = value
        self.comment_brush = wx.Brush(self.comment_background_color, wx.SOLID)

    @property
    def empty_background_color(self):
        return self._empty_background_color

    @empty_background_color.setter
    def empty_background_color(self, value):
        self._empty_background_color = value
        self.empty_brush = wx.Brush(self.empty_background_color, wx.SOLID)

    def calc_cell_size_in_pixels(self, chars_per_cell):
        width = self.cell_padding_width * 2 + self.text_font_char_width * chars_per_cell
        height = self.row_height_extra_padding + self.text_font_char_height
        return width, height

    def calc_text_width(self, text):
        return self.text_font_char_width * len(text)


def find_application_preferences(prefs_module):
    mod = importlib.import_module(prefs_module)
    prefs_cls = SawxApplicationPreferences
    for name, obj in inspect.getmembers(mod):
        if inspect.isclass(obj) and SawxApplicationPreferences in obj.__mro__[1:]:
            prefs_cls = obj
            break
    return prefs_cls(prefs_module)


def find_editor_preferences(prefs_module):
    mod = importlib.import_module(prefs_module)
    prefs_cls = SawxEditorPreferences
    for name, obj in inspect.getmembers(mod):
        if inspect.isclass(obj) and SawxEditorPreferences in obj.__mro__[1:]:
            prefs_cls = obj
            break
    return prefs_cls(prefs_module)
