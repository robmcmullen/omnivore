"""Byte modification actions
"""
import os
import sys

import wx

from sawx.ui import dialogs

from . import ViewerAction, ViewerListAction, ViewerRadioListAction
from ... import commands
from ...disassembler.valid_cpus import cpu_id_to_name, valid_cpu_ids

import logging
log = logging.getLogger(__name__)


class disasm_type(ViewerListAction):
    def calc_enabled(self, action_key):
       return self.viewer.control.caret_handler.has_selection

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return item[1]

    def calc_list_items(self):
        d = [(id, name) for id, name in cpu_id_to_name.items() if id not in valid_cpu_ids]
        d.sort()
        d[0:0] = [(128, "Code")]
        return d

    def perform(self, action_key):
        item = self.get_item(action_key)
        disasm_type = item[0]
        e = self.editor
        ranges = self.viewer.control.get_selected_ranges()
        cmd = commands.SetDisasmCommand(e.segment, ranges, disasm_type)
        e.process_command(cmd)
