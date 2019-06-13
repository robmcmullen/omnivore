"""Segment actions
"""
import os
import sys

import wx

from sawx.action import SawxAction
from sawx.ui.minibuffer import NextPrevTextMinibuffer

from .. import commands
from ... import errors

import logging
log = logging.getLogger(__name__)


class find(SawxAction):
    def calc_name(self, action_key):
        return "Find"

    def get_minibuffer(self, action_key):
        e = self.editor
        control = NextPrevTextMinibuffer(e, commands.FindAllCommand, commands.FindNextCommand, commands.FindPrevCommand, initial=e.last_search_settings["find"])
        return control

    def perform(self, action_key):
        minibuffer = self.get_minibuffer(action_key)
        self.editor.control.show_minibuffer(minibuffer)


class find_to_selection(SawxAction):
    def calc_name(self, action_key):
        return "Find to Selection"

    def perform(self, action_key):
        e = self.editor
        v = e.focused_viewer
        e.control.on_hide_minibuffer_or_cancel(True)  # refreshes current control, but others need refreshing
        v.segment.convert_style({'match':True}, {'selected':True})
        v.control.caret_handler.convert_style_to_carets()
        flags = e.calc_status_flags()
        flags.refresh_needed = True
        flags.sync_caret_from_control = v.control
        # flags.refreshed_as_side_effect.add(v.control)
        e.process_flags(flags)
