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
        pass

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
        self.num_open_recent = 15
        self.confirm_before_close = True


class SawxEditorPreferences(SawxPreferences):
    display_order = [
        ("text_font", "wx.Font"),
        ("text_color", "wx.Colour"),
        ("background_color", "wx.Colour"),
        ("empty_background_color", "wx.Colour"),
    ]

    def set_defaults(self):
        self.text_font = fonts.str_to_font(fonts.default_font)
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
