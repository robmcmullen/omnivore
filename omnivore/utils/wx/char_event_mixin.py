import wx

from omnivore.utils.command import DisplayFlags

import logging
log = logging.getLogger(__name__)


class CharEventMixin(object):
    """Mixin object to create a standard interface for controls that have
    caret movement.

    Note: on MAC, wx.MOD_CONTROL refers to the "command" key and
    wx.MOD_RAW_CONTROL refers to the actual "control" key and have different
    values. On other platforms, wx.MOD_CONTROL and wx.MOD_RAW_CONTROL point to
    the same key on the keyboard and have the same value.
    """

    char_event_movement_default = {
        (wx.WXK_DOWN,      wx.MOD_NONE): 'handle_char_move_down',
        (wx.WXK_UP,        wx.MOD_NONE): 'handle_char_move_up',
        (wx.WXK_LEFT,      wx.MOD_NONE): 'handle_char_move_left',
        (wx.WXK_RIGHT,     wx.MOD_NONE): 'handle_char_move_right',
        (wx.WXK_PAGEDOWN,  wx.MOD_NONE): 'handle_char_move_page_down',
        (wx.WXK_PAGEUP,    wx.MOD_NONE): 'handle_char_move_page_up',
        (wx.WXK_HOME,      wx.MOD_NONE): 'handle_char_move_start_of_line',
        (wx.WXK_END,       wx.MOD_NONE): 'handle_char_move_end_of_line',
        (wx.WXK_BACK,      wx.MOD_NONE): 'handle_char_move_backspace',
        (wx.WXK_DELETE,    wx.MOD_NONE): 'handle_char_move_delete',
        (wx.WXK_RETURN,    wx.MOD_NONE): 'handle_char_move_next',
        (wx.WXK_ESCAPE,    wx.MOD_NONE): 'handle_char_cancel',
        (wx.WXK_TAB,       wx.MOD_NONE): 'handle_char_move_next_line',
        (wx.WXK_SPACE,     wx.MOD_NONE): 'handle_char_move_next',

    # control:  CMD on mac!
        (wx.WXK_HOME,      wx.MOD_CONTROL): 'handle_char_move_start_of_file',
        (wx.WXK_END,       wx.MOD_CONTROL): 'handle_char_move_end_of_file',
        ('c',              wx.MOD_CONTROL): 'handle_char_copy_selection',
        ('d',              wx.MOD_CONTROL): 'handle_char_delete_selection',
        ('v',              wx.MOD_CONTROL): 'handle_char_paste',
        ('x',              wx.MOD_CONTROL): 'handle_char_cut_selection',
        (wx.WXK_INSERT,    wx.MOD_CONTROL): 'handle_char_copy_selection',

    # shift:
        (wx.WXK_DELETE,    wx.MOD_SHIFT): 'handle_char_cut_selection',
        (wx.WXK_INSERT,    wx.MOD_SHIFT): 'handle_char_paste',

    # alt:

    }

    char_event_edit_line_default = {
        (wx.WXK_DOWN,      wx.MOD_NONE): 'handle_char_edit_next_history',
        (wx.WXK_UP,        wx.MOD_NONE): 'handle_char_edit_previous_history',
        (wx.WXK_LEFT,      wx.MOD_NONE): 'handle_char_edit_left',
        (wx.WXK_RIGHT,     wx.MOD_NONE): 'handle_char_edit_right',
        (wx.WXK_HOME,      wx.MOD_NONE): 'handle_char_edit_start_of_line',
        (wx.WXK_END,       wx.MOD_NONE): 'handle_char_edit_end_of_line',
        (wx.WXK_BACK,      wx.MOD_NONE): 'handle_char_edit_backspace',
        (wx.WXK_DELETE,    wx.MOD_NONE): 'handle_char_edit_delete',
        (wx.WXK_RETURN,    wx.MOD_NONE): 'handle_char_edit_finished',
        (wx.WXK_ESCAPE,    wx.MOD_NONE): 'handle_char_edit_cancel',
        (wx.WXK_TAB,       wx.MOD_NONE): 'handle_char_edit_finished',
        (wx.WXK_SPACE,     wx.MOD_NONE): 'handle_char_edit_space',

    # control:  CMD on mac!
        ('c',              wx.MOD_CONTROL): 'handle_char_edit_copy_selection',
        ('d',              wx.MOD_CONTROL): 'handle_char_edit_delete_selection',
        ('v',              wx.MOD_CONTROL): 'handle_char_edit_paste',
        ('x',              wx.MOD_CONTROL): 'handle_char_edit_cut_selection',
        (wx.WXK_INSERT,    wx.MOD_CONTROL): 'handle_char_edit_copy_selection',

    # shift:
        (wx.WXK_DELETE,    wx.MOD_SHIFT): 'handle_char_edit_cut_selection',
        (wx.WXK_INSERT,    wx.MOD_SHIFT): 'handle_char_edit_paste',

    # alt:

    }


    def __init__(self, caret_handler):
        self.caret_handler = caret_handler
        self.char_event_movement = self.char_event_movement_default.copy()
        self.char_event_line_edit = self.char_event_edit_line_default.copy()

        self.current_char_event_map = self.char_event_movement

    def map_char_events(self, source):
        source.Bind(wx.EVT_CHAR, self.on_char)

    def create_char_event_flags(self):
        flags = DisplayFlags(self)
        flags.old_carets = set(self.caret_handler.calc_caret_state())
        return flags

    def on_char(self, evt):
        key = evt.GetKeyCode()
        mods = evt.GetModifiers()
        specifier = (key, mods)
        try:
            handler = self.current_char_event_map[specifier]
        except KeyError:
            log.debug("No handler for keyboard event: key=%d mods=%d" % (key, mods))
            evt.Skip()
        else:
            try:
                func = getattr(self, handler)
            except AttributeError:
                log.error("handler %s defined for key=%d mods=%d but missing!" % (handler, key, mods))
                evt.Skip()
            else:
                log.debug("using handler %s" % handler)
                flags = self.create_char_event_flags()
                func(evt, flags)
                self.caret_handler.process_flags(flags)
